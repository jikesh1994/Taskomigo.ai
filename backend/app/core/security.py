"""Password hashing, JWT access tokens and opaque refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.exceptions import AuthenticationError

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - token type label, not a secret

_password_hasher = PasswordHasher()
# Used to equalize timing when the user does not exist (prevents account enumeration).
_DUMMY_HASH = _password_hasher.hash(secrets.token_urlsafe(16))


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_aware(value: datetime) -> datetime:
    """Treat naive datetimes (e.g. read back from SQLite) as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def burn_password_check(password: str) -> None:
    """Spend the same CPU time as a real verification without a real user."""
    verify_password(password, _DUMMY_HASH)


@dataclass(frozen=True, slots=True)
class AccessTokenPayload:
    user_id: uuid.UUID
    role: str
    jti: str
    expires_at: datetime


def create_access_token(user_id: uuid.UUID, role: str, settings: Settings) -> tuple[str, int]:
    """Return (token, lifetime_seconds)."""
    now = utc_now()
    lifetime = timedelta(minutes=settings.access_token_ttl_minutes)
    claims = {
        "sub": str(user_id),
        "role": role,
        "typ": ACCESS_TOKEN_TYPE,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(
        claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str, settings: Settings) -> AccessTokenPayload:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iat", "typ", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token has expired.", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid access token.", code="invalid_token") from exc

    if claims.get("typ") != ACCESS_TOKEN_TYPE:
        raise AuthenticationError("Invalid access token.", code="invalid_token")
    try:
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, TypeError) as exc:
        raise AuthenticationError("Invalid access token.", code="invalid_token") from exc
    return AccessTokenPayload(
        user_id=user_id,
        role=str(claims.get("role", "")),
        jti=claims["jti"],
        expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
    )


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Refresh tokens are high-entropy, so a fast hash is enough; only the hash is stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
