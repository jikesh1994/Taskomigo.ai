from __future__ import annotations

from app.core.config import Settings
from app.core.encryption import EncryptionService
from app.core.exceptions import ConfigurationError
from app.storage.base import ObjectStorage
from app.storage.encrypted import EncryptedStorage
from app.storage.local import LocalStorage
from app.storage.s3 import GCS_S3_ENDPOINT, S3Storage


def _secret(value: object) -> str | None:
    return value.get_secret_value() if value is not None else None  # type: ignore[attr-defined]


def create_storage(settings: Settings) -> ObjectStorage:
    """The configured backend, wrapped so every object is encrypted at rest."""
    inner: ObjectStorage
    if settings.storage_backend == "local":
        inner = LocalStorage(settings.storage_local_path)
    else:
        if not settings.storage_bucket:
            raise ConfigurationError("STORAGE_BUCKET is required for the s3/gcs storage backends.")
        endpoint = settings.storage_endpoint_url or (
            GCS_S3_ENDPOINT if settings.storage_backend == "gcs" else None
        )
        inner = S3Storage(
            bucket=settings.storage_bucket,
            access_key=_secret(settings.storage_access_key),
            secret_key=_secret(settings.storage_secret_key),
            endpoint_url=endpoint,
            region=settings.storage_region,
        )
    return EncryptedStorage(inner, EncryptionService.from_settings(settings))
