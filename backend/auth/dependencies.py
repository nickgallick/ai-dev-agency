"""FastAPI dependencies for authentication.

Phase 9B: JWT authentication middleware.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from models.database import get_db
from .models import User
from .utils import decode_token

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for Swagger UI
bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    access_token: Optional[str] = Cookie(None),
) -> Optional[str]:
    """Extract JWT token from Authorization header or cookie.
    
    Priority:
    1. Authorization: Bearer <token> header
    2. access_token cookie (httpOnly)
    """
    # Try header first
    if credentials and credentials.credentials:
        return credentials.credentials
    
    # Try cookie
    if access_token:
        return access_token
    
    return None


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get the current authenticated user from JWT token.
    
    Returns None if not authenticated (for optional auth).
    """
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    # Check token type
    if payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    try:
        user = db.query(User).filter(
            User.id == UUID(user_id),
            User.is_active == True
        ).first()
        return user
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authentication - raises 401 if not authenticated.
    
    Use this as a dependency for protected routes.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def is_setup_complete(db: Session = Depends(get_db)) -> bool:
    """Check if initial setup is complete (user exists)."""
    user_count = db.query(User).count()
    return user_count > 0


async def require_setup_incomplete(
    is_complete: bool = Depends(is_setup_complete),
) -> None:
    """Require that setup is NOT complete.
    
    Used for the initial setup endpoint.
    """
    if is_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already complete",
        )
