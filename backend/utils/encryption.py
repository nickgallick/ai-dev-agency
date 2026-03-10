"""Encryption utilities for secure credential storage."""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _get_fernet() -> Fernet:
    """Get Fernet instance using master key from environment."""
    master_key = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
    salt = b"ai-dev-agency-salt"  # In production, use a random salt stored securely
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    return Fernet(key)


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential string."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a credential string."""
    fernet = _get_fernet()
    encrypted = base64.urlsafe_b64decode(ciphertext.encode())
    decrypted = fernet.decrypt(encrypted)
    return decrypted.decode()
