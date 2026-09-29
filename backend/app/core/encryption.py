"""Symmetric encryption for secrets at rest (e.g. browser-session references).

Uses MultiFernet so keys can be rotated: the first key encrypts, every key decrypts.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import Settings
from app.core.exceptions import ConfigurationError


class DecryptionError(Exception):
    """Ciphertext is invalid, tampered with, or was encrypted with an unknown key."""


class EncryptionService:
    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ConfigurationError("At least one encryption key is required (ENCRYPTION_KEYS).")
        try:
            self._fernet = MultiFernet([Fernet(k.encode()) for k in keys])
        except (ValueError, TypeError) as exc:
            raise ConfigurationError("ENCRYPTION_KEYS contains an invalid Fernet key.") from exc

    @classmethod
    def from_settings(cls, settings: Settings) -> EncryptionService:
        return cls(settings.encryption_key_list)

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise DecryptionError("Unable to decrypt value.") from exc

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, token: bytes) -> bytes:
        try:
            return self._fernet.decrypt(token)
        except (InvalidToken, ValueError) as exc:
            raise DecryptionError("Unable to decrypt value.") from exc

    def rotate(self, ciphertext: str) -> str:
        """Re-encrypt a value with the current primary key."""
        try:
            return self._fernet.rotate(ciphertext.encode("ascii")).decode("ascii")
        except (InvalidToken, ValueError) as exc:
            raise DecryptionError("Unable to rotate value.") from exc
