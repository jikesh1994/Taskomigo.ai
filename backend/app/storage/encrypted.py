from __future__ import annotations

from app.core.encryption import DecryptionError, EncryptionService
from app.storage.base import ObjectStorage, StorageError


class EncryptedStorage:
    """Encrypts objects with the application key before they reach the backend.

    Resumes are personal data; encrypting in the app means a leaked bucket or disk
    image alone exposes nothing, whatever the backend's own encryption settings.
    """

    def __init__(self, inner: ObjectStorage, encryption: EncryptionService) -> None:
        self._inner = inner
        self._encryption = encryption

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await self._inner.put(
            key, self._encryption.encrypt_bytes(data), content_type="application/octet-stream"
        )

    async def get(self, key: str) -> bytes:
        token = await self._inner.get(key)
        try:
            return self._encryption.decrypt_bytes(token)
        except DecryptionError as exc:
            raise StorageError(f"Stored object {key!r} could not be decrypted") from exc

    async def delete(self, key: str) -> None:
        await self._inner.delete(key)
