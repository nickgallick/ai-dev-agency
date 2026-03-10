"""AES-256 encryption utilities for secure credential storage."""

import os
import base64
import hashlib
import logging
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

# AES block size
BLOCK_SIZE = 16


def _get_encryption_key() -> bytes:
    """Get the 32-byte encryption key from settings.
    
    Returns:
        32-byte key for AES-256 encryption.
        
    Raises:
        ValueError: If encryption key is not configured or invalid.
    """
    settings = get_settings()
    key_hex = settings.encryption_key
    
    if not key_hex:
        raise ValueError(
            "ENCRYPTION_KEY not configured. "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    
    try:
        key_bytes = bytes.fromhex(key_hex)
        if len(key_bytes) != 32:
            raise ValueError(
                f"ENCRYPTION_KEY must be 32 bytes (64 hex chars), got {len(key_bytes)} bytes"
            )
        return key_bytes
    except Exception as e:
        logger.error("Failed to parse encryption key")
        raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using AES-256-CBC.
    
    Args:
        plaintext: The string to encrypt.
        
    Returns:
        Base64-encoded string containing IV + ciphertext.
    """
    if not plaintext:
        return ""
    
    key = _get_encryption_key()
    
    # Generate random IV
    iv = os.urandom(BLOCK_SIZE)
    
    # Pad plaintext to block size (PKCS7 padding)
    plaintext_bytes = plaintext.encode('utf-8')
    padding_length = BLOCK_SIZE - (len(plaintext_bytes) % BLOCK_SIZE)
    padded_data = plaintext_bytes + bytes([padding_length] * padding_length)
    
    # Encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # Combine IV + ciphertext and base64 encode
    encrypted_data = iv + ciphertext
    return base64.b64encode(encrypted_data).decode('utf-8')


def decrypt_value(encrypted: str) -> str:
    """Decrypt a value encrypted with encrypt_value.
    
    Args:
        encrypted: Base64-encoded string containing IV + ciphertext.
        
    Returns:
        Decrypted plaintext string.
    """
    if not encrypted:
        return ""
    
    key = _get_encryption_key()
    
    # Decode base64
    encrypted_data = base64.b64decode(encrypted.encode('utf-8'))
    
    # Extract IV and ciphertext
    iv = encrypted_data[:BLOCK_SIZE]
    ciphertext = encrypted_data[BLOCK_SIZE:]
    
    # Decrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # Remove PKCS7 padding
    padding_length = padded_data[-1]
    plaintext_bytes = padded_data[:-padding_length]
    
    return plaintext_bytes.decode('utf-8')


def hash_credential_key(server_name: str, credential_key: str) -> str:
    """Create a deterministic hash for credential lookup.
    
    Args:
        server_name: Name of the MCP server.
        credential_key: Key name for the credential.
        
    Returns:
        SHA-256 hash of the combined key.
    """
    combined = f"{server_name}:{credential_key}"
    return hashlib.sha256(combined.encode()).hexdigest()
