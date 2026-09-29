"""Declarative base, naming conventions and shared column mixins.

Column types are portable (Uuid, JSON->JSONB on PostgreSQL, non-native enums) so the
schema is identical on PostgreSQL in production and SQLite in fast unit tests.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, MetaData, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.security import utc_now

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        dict[str, Any]: JSONType,
        dict[str, int]: JSONType,
        list[str]: JSONType,
        list[dict[str, str]]: JSONType,
        uuid.UUID: Uuid(),
        datetime: DateTime(timezone=True),
    }


def str_enum(enum_cls: type[enum.Enum], length: int = 32) -> Enum:
    """Store enums as validated VARCHAR (no native PG enum -> painless migrations)."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False
    )
