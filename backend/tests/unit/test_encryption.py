from __future__ import annotations

import pytest

from app.core.encryption import DecryptionError, EncryptionService
from app.core.exceptions import ConfigurationError


def test_roundtrip() -> None:
    service = EncryptionService([EncryptionService.generate_key()])
    ciphertext = service.encrypt("session-ref-123")
    assert "session-ref-123" not in ciphertext
    assert service.decrypt(ciphertext) == "session-ref-123"


def test_key_rotation() -> None:
    old_key, new_key = EncryptionService.generate_key(), EncryptionService.generate_key()
    old = EncryptionService([old_key])
    ciphertext = old.encrypt("secret")

    rotated_service = EncryptionService([new_key, old_key])
    assert rotated_service.decrypt(ciphertext) == "secret"
    rotated = rotated_service.rotate(ciphertext)
    assert EncryptionService([new_key]).decrypt(rotated) == "secret"


def test_tampered_or_foreign_ciphertext_rejected() -> None:
    service = EncryptionService([EncryptionService.generate_key()])
    other = EncryptionService([EncryptionService.generate_key()])
    with pytest.raises(DecryptionError):
        service.decrypt(other.encrypt("x"))
    with pytest.raises(DecryptionError):
        service.decrypt("not-a-token")


def test_missing_or_invalid_keys_rejected() -> None:
    with pytest.raises(ConfigurationError):
        EncryptionService([])
    with pytest.raises(ConfigurationError):
        EncryptionService(["too-short"])
