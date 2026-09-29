"""Object storage for user files (resumes). See `factory.create_storage`."""

from app.storage.base import ObjectNotFoundError, ObjectStorage, StorageError

__all__ = ["ObjectNotFoundError", "ObjectStorage", "StorageError"]
