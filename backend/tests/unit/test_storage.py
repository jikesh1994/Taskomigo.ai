from __future__ import annotations

from pathlib import Path

import boto3
import pytest
from cryptography.fernet import Fernet
from moto import mock_aws

from app.core.config import Settings
from app.core.encryption import EncryptionService
from app.storage import ObjectNotFoundError
from app.storage.base import validate_key
from app.storage.encrypted import EncryptedStorage
from app.storage.factory import create_storage
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


async def test_local_storage_roundtrip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    await storage.put("resumes/u/r", b"hello", content_type="application/pdf")
    assert await storage.get("resumes/u/r") == b"hello"
    await storage.delete("resumes/u/r")
    await storage.delete("resumes/u/r")  # idempotent
    with pytest.raises(ObjectNotFoundError):
        await storage.get("resumes/u/r")


@pytest.mark.parametrize("key", ["../etc/passwd", "a/../../b", "/abs", "a//b", "", "with space"])
def test_keys_cannot_escape_the_root(key: str) -> None:
    with pytest.raises(ValueError):
        validate_key(key)


async def test_encrypted_storage_never_writes_plaintext(tmp_path: Path) -> None:
    inner = LocalStorage(tmp_path)
    storage = EncryptedStorage(inner, EncryptionService([Fernet.generate_key().decode()]))
    secret = b"%PDF-1.7 Priya Sharma priya@example.com"
    await storage.put("resumes/u/r", secret, content_type="application/pdf")

    on_disk = (tmp_path / "resumes/u/r").read_bytes()
    assert b"Priya" not in on_disk and on_disk != secret
    assert await storage.get("resumes/u/r") == secret


async def test_s3_storage_roundtrip() -> None:
    # mock_aws as a context manager: its decorator form doesn't wrap coroutines.
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="resumes-test")
        storage = S3Storage(bucket="resumes-test", client=client)

        await storage.put("resumes/u/r", b"data", content_type="application/pdf")
        assert await storage.get("resumes/u/r") == b"data"
        await storage.delete("resumes/u/r")
        with pytest.raises(ObjectNotFoundError):
            await storage.get("resumes/u/r")


def test_factory_builds_encrypted_backends(tmp_path: Path) -> None:
    key = Fernet.generate_key().decode()
    local = create_storage(
        Settings(_env_file=None, encryption_keys=key, storage_local_path=str(tmp_path))
    )
    assert isinstance(local, EncryptedStorage)
    gcs = create_storage(
        Settings(
            _env_file=None,
            encryption_keys=key,
            storage_backend="gcs",
            storage_bucket="b",
            storage_access_key="GOOG1",
            storage_secret_key="secret",
        )
    )
    assert isinstance(gcs._inner, S3Storage)  # type: ignore[attr-defined]
    assert gcs._inner._client.meta.endpoint_url == "https://storage.googleapis.com"  # type: ignore[attr-defined]
