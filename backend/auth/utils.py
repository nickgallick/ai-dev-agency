"""Authentication utilities.

Phase 9B: Password hashing and JWT token management.
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import bcrypt
import jwt

# JWT Configuration
JWT_SECRET = os.getenv("SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
IDLE_TIMEOUT_MINUTES = 30


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        password: Plain text password
        password_hash: Bcrypt hash
        
    Returns:
        True if password matches
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception:
        return False


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: User's UUID
        email: User's email
        expires_delta: Optional custom expiry time
        
    Returns:
        Encoded JWT string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """Create a refresh token.
    
    Args:
        user_id: User's UUID
        expires_delta: Optional custom expiry time
        
    Returns:
        Tuple of (token string, expiry datetime)
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.utcnow() + expires_delta
    
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    
    payload = {
        "sub": user_id,
        "type": "refresh",
        "token": token,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded, expire


def hash_token(token: str) -> str:
    """Hash a token for storage.
    
    Args:
        token: Raw token string
        
    Returns:
        SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token.
    
    Args:
        token: Encoded JWT string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def check_idle_timeout(last_activity: datetime) -> bool:
    """Check if the session has exceeded idle timeout.
    
    Args:
        last_activity: Timestamp of last user activity
        
    Returns:
        True if session is still valid (not timed out)
    """
    if last_activity is None:
        return False
    
    timeout = timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    return datetime.utcnow() - last_activity < timeout
