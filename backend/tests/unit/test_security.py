from __future__ import annotations

import uuid
from pathlib import Path

import jwt
import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from tests.conftest import make_settings


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cure-password")
    assert hashed.startswith("$argon2id$")
    assert "s3cure-password" not in hashed
    assert verify_password("s3cure-password", hashed)
    assert not verify_password("wrong-password", hashed)
    assert not password_needs_rehash(hashed)


def test_verify_password_handles_garbage_hash() -> None:
    assert not verify_password("anything", "not-a-hash")
    assert password_needs_rehash("not-a-hash")


def test_access_token_roundtrip(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    user_id = uuid.uuid4()
    token, lifetime = create_access_token(user_id, "user", settings)
    assert lifetime == settings.access_token_ttl_minutes * 60
    payload = decode_access_token(token, settings)
    assert payload.user_id == user_id
    assert payload.role == "user"


def test_expired_access_token_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "typ": "access",
            "iss": settings.jwt_issuer,
            "iat": 1,
            "exp": 2,
            "jti": "x",
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError) as exc:
        decode_access_token(token, settings)
    assert exc.value.code == "token_expired"


def test_token_signed_with_other_secret_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    other = make_settings(tmp_path, jwt_secret="another-secret-" + "z" * 32)
    token, _ = create_access_token(uuid.uuid4(), "user", other)
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


def test_wrong_token_type_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "typ": "refresh",
            "iss": settings.jwt_issuer,
            "iat": 1,
            "exp": 9_999_999_999,
            "jti": "x",
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


def test_alg_none_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "typ": "access",
            "iss": settings.jwt_issuer,
            "iat": 1,
            "exp": 9_999_999_999,
            "jti": "x",
        },
        key="",
        algorithm="none",
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


def test_refresh_tokens_are_random_and_hash_is_stable() -> None:
    a, b = generate_refresh_token(), generate_refresh_token()
    assert a != b and len(a) >= 60
    assert hash_token(a) == hash_token(a)
    assert hash_token(a) != hash_token(b)
    assert len(hash_token(a)) == 64
