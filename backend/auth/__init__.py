"""Authentication module for AI Dev Agency.

Phase 9B: Single-user JWT authentication.
"""

from .models import User, RefreshToken
from .utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from .dependencies import get_current_user, require_auth
from .routes import router as auth_router

__all__ = [
    "User",
    "RefreshToken",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "require_auth",
    "auth_router",
]
