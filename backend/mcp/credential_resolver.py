"""Credential resolution for MCP servers.

Resolves credentials from UI storage (priority) or environment variables.
UI credentials are stored encrypted in PostgreSQL.
"""

import logging
from typing import Optional
import os

from backend.utils.crypto import decrypt_value, hash_credential_key
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

# In-memory cache for resolved credentials (cleared on restart)
_credential_cache: dict = {}


async def get_credential(
    server_name: str,
    credential_key: str,
    use_cache: bool = True
) -> Optional[str]:
    """Get a credential value for an MCP server.
    
    Priority order:
    1. UI-stored encrypted credentials (PostgreSQL)
    2. Environment variables
    
    Args:
        server_name: Name of the MCP server.
        credential_key: Key name for the credential.
        use_cache: Whether to use in-memory cache.
        
    Returns:
        Decrypted credential value, or None if not found.
    """
    cache_key = f"{server_name}:{credential_key}"
    
    if use_cache and cache_key in _credential_cache:
        return _credential_cache[cache_key]
    
    # Try UI credentials first
    ui_credential = await _get_ui_credential(server_name, credential_key)
    if ui_credential:
        if use_cache:
            _credential_cache[cache_key] = ui_credential
        return ui_credential
    
    # Fall back to environment variable
    env_credential = _get_env_credential(server_name, credential_key)
    if env_credential and use_cache:
        _credential_cache[cache_key] = env_credential
    
    return env_credential


async def _get_ui_credential(server_name: str, credential_key: str) -> Optional[str]:
    """Get credential from UI storage (encrypted in database)."""
    try:
        # Import here to avoid circular imports
        from backend.api.database import get_db_session
        from sqlalchemy import text
        
        credential_id = hash_credential_key(server_name, credential_key)
        
        async with get_db_session() as session:
            result = await session.execute(
                text("SELECT encrypted_value FROM mcp_credentials WHERE id = :id"),
                {"id": credential_id}
            )
            row = result.fetchone()
            
            if row and row[0]:
                return decrypt_value(row[0])
    except Exception as e:
        # Log without exposing credential details
        logger.debug(f"UI credential lookup failed for {server_name}")
    
    return None


def _get_env_credential(server_name: str, credential_key: str) -> Optional[str]:
    """Get credential from environment variable."""
    settings = get_settings()
    
    # Map server/key combinations to settings attributes
    credential_map = {
        ("github", "token"): settings.github_token,
        ("slack", "webhook_url"): settings.slack_webhook_url,
        ("notion", "token"): settings.notion_token,
        ("postgres", "database_url"): settings.database_url,
    }
    
    return credential_map.get((server_name, credential_key))


async def set_credential(
    server_name: str,
    credential_key: str,
    value: str
) -> bool:
    """Store an encrypted credential in the database.
    
    Args:
        server_name: Name of the MCP server.
        credential_key: Key name for the credential.
        value: Plaintext credential value (will be encrypted).
        
    Returns:
        True if stored successfully.
    """
    try:
        from backend.api.database import get_db_session
        from backend.utils.crypto import encrypt_value
        from sqlalchemy import text
        
        credential_id = hash_credential_key(server_name, credential_key)
        encrypted = encrypt_value(value)
        
        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO mcp_credentials (id, server_name, credential_key, encrypted_value)
                    VALUES (:id, :server, :key, :value)
                    ON CONFLICT (id) DO UPDATE SET
                        encrypted_value = EXCLUDED.encrypted_value,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {
                    "id": credential_id,
                    "server": server_name,
                    "key": credential_key,
                    "value": encrypted,
                }
            )
            await session.commit()
        
        # Clear cache
        cache_key = f"{server_name}:{credential_key}"
        _credential_cache.pop(cache_key, None)
        
        logger.info(f"Credential stored for {server_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store credential for {server_name}: {e}")
        return False


async def delete_credential(server_name: str, credential_key: str) -> bool:
    """Delete a credential from the database."""
    try:
        from backend.api.database import get_db_session
        from sqlalchemy import text
        
        credential_id = hash_credential_key(server_name, credential_key)
        
        async with get_db_session() as session:
            await session.execute(
                text("DELETE FROM mcp_credentials WHERE id = :id"),
                {"id": credential_id}
            )
            await session.commit()
        
        # Clear cache
        cache_key = f"{server_name}:{credential_key}"
        _credential_cache.pop(cache_key, None)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        return False


def clear_credential_cache() -> None:
    """Clear the in-memory credential cache."""
    _credential_cache.clear()
