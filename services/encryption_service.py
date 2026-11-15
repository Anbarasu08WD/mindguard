import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


class EncryptionService:
    """Service handling field-level Fernet symmetric encryption for sensitive data."""

    @staticmethod
    def _get_fernet() -> Fernet:
        key = current_app.config.get("FERNET_KEY") if current_app else os.getenv("FERNET_KEY")
        if not key:
            raise ValueError("FERNET_KEY is not configured in the application environment.")
        if isinstance(key, str):
            key = key.strip().encode()
        return Fernet(key)

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypts plaintext string using Fernet and returns a base64 string."""
        if plaintext is None:
            return ""
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        fernet = cls._get_fernet()
        ciphertext_bytes = fernet.encrypt(plaintext.encode("utf-8"))
        return ciphertext_bytes.decode("utf-8")

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """Decrypts Fernet ciphertext string and returns original plaintext."""
        if not ciphertext:
            return ""
        fernet = cls._get_fernet()
        try:
            decrypted_bytes = fernet.decrypt(ciphertext.strip().encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            return "[Decryption failed: Invalid or altered cryptographic token]"
        except Exception:
            return "[Decryption failed: Error during record decryption]"
