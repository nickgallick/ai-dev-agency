"""Authentication API routes.

Phase 9B: Single-user JWT authentication.

Endpoints:
- POST /api/auth/setup - Initial admin account creation
- POST /api/auth/login - Email + password → JWT tokens
- POST /api/auth/refresh - Refresh token → new access token
- POST /api/auth/logout - Invalidate refresh token
- GET /api/auth/me - Get current user info
- GET /api/auth/status - Check if setup is complete
"""
import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from models.database import get_db
from .models import User, RefreshToken
from .utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .dependencies import (
    get_current_user,
    require_auth,
    is_setup_complete,
    require_setup_incomplete,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============ Request/Response Models ============

class SetupRequest(BaseModel):
    """Initial setup request."""
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: Optional[str] = None  # Can also come from cookie


class AuthResponse(BaseModel):
    """Authentication response with tokens."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class StatusResponse(BaseModel):
    """Setup status response."""
    setup_complete: bool
    user_exists: bool


class UserResponse(BaseModel):
    """User info response."""
    id: str
    email: str
    name: Optional[str]
    last_login: Optional[str]
    created_at: str


# ============ Endpoints ============

@router.get("/status", response_model=StatusResponse)
async def get_auth_status(db: Session = Depends(get_db)):
    """Check if initial setup is complete.
    
    Returns whether a user account exists.
    """
    user_count = db.query(User).count()
    return StatusResponse(
        setup_complete=user_count > 0,
        user_exists=user_count > 0,
    )


@router.post("/setup", response_model=AuthResponse)
async def setup_admin(
    request: SetupRequest,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_setup_incomplete),
):
    """Create the initial admin account.
    
    Only works if no users exist yet.
    """
    # Check for bootstrap credentials in environment
    bootstrap_email = os.getenv("ADMIN_EMAIL")
    bootstrap_hash = os.getenv("ADMIN_PASSWORD_HASH")
    
    if bootstrap_email and bootstrap_hash:
        # Verify the provided email matches bootstrap
        if request.email != bootstrap_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email must match ADMIN_EMAIL environment variable",
            )
        # Use the pre-hashed password from environment
        password_hash = bootstrap_hash
    else:
        # Hash the provided password
        if len(request.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )
        password_hash = hash_password(request.password)
    
    # Create user
    user = User(
        email=request.email,
        password_hash=password_hash,
        name=request.name or "Admin",
        last_login=datetime.utcnow(),
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin account created: {user.email}")
    
    # Generate tokens
    access_token = create_access_token(str(user.id), user.email)
    refresh_token, refresh_expires = create_refresh_token(str(user.id))
    
    # Store refresh token hash
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires,
    )
    db.add(token_record)
    db.commit()
    
    # Set httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )
    
    return AuthResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict(),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate with email and password.
    
    Returns JWT access token and sets httpOnly refresh token cookie.
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    logger.info(f"User logged in: {user.email}")
    
    # Generate tokens
    access_token = create_access_token(str(user.id), user.email)
    refresh_token, refresh_expires = create_refresh_token(str(user.id))
    
    # Store refresh token hash
    device_info = http_request.headers.get("User-Agent", "Unknown")[:500]
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires,
        device_info=device_info,
    )
    db.add(token_record)
    db.commit()
    
    # Cookie max age based on remember_me
    cookie_max_age = 7 * 24 * 60 * 60 if request.remember_me else ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    # Set httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=cookie_max_age,
    )
    
    return AuthResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict(),
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    response: Response,
    request: RefreshRequest = None,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    db: Session = Depends(get_db),
):
    """Refresh the access token using a refresh token.
    
    Accepts refresh token from:
    1. Request body (refresh_token field)
    2. Cookie (refresh_token)
    """
    # Get refresh token from body or cookie
    token = None
    if request and request.refresh_token:
        token = request.refresh_token
    elif refresh_token_cookie:
        token = refresh_token_cookie
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    
    # Decode and validate token
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Check if token is in database and not revoked
    token_hash = hash_token(token)
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow(),
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or expired",
        )
    
    # Get user
    from uuid import UUID
    user = db.query(User).filter(
        User.id == UUID(user_id),
        User.is_active == True,
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Generate new access token
    access_token = create_access_token(str(user.id), user.email)
    
    # Set new access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return AuthResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user.to_dict(),
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout and invalidate refresh token.
    
    Revokes the refresh token and clears cookies.
    """
    # Revoke refresh token if provided
    if refresh_token_cookie:
        token_hash = hash_token(refresh_token_cookie)
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
        ).first()
        
        if token_record:
            token_record.is_revoked = True
            token_record.revoked_at = datetime.utcnow()
            db.commit()
    
    if user:
        logger.info(f"User logged out: {user.email}")
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    """Get current user info.
    
    Requires authentication.
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Change the user's password.
    
    Requires current password verification.
    """
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )
    
    # Update password
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Password changed for user: {user.email}")
    
    return {"message": "Password changed successfully"}


@router.post("/revoke-all-sessions")
async def revoke_all_sessions(
    response: Response,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Revoke all refresh tokens for the current user.
    
    Forces re-authentication on all devices.
    """
    # Revoke all refresh tokens
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False,
    ).update({
        RefreshToken.is_revoked: True,
        RefreshToken.revoked_at: datetime.utcnow(),
    })
    db.commit()
    
    # Clear current session cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    logger.info(f"All sessions revoked for user: {user.email}")
    
    return {"message": "All sessions revoked"}
