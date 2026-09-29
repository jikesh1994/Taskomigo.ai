"""resumes

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _enum(name: str, length: int, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=length)


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_type", _enum("resumefiletype", 8, "pdf", "docx"), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "parse_status",
            _enum("resumeparsestatus", 16, "pending", "processing", "parsed", "failed"),
            nullable=False,
        ),
        sa.Column("parse_error_code", sa.String(64), nullable=True),
        sa.Column("parse_error", sa.String(500), nullable=True),
        sa.Column("parsed_text", sa.Text(), nullable=True),
        sa.Column("parsed_data", JSON, nullable=True),
        sa.Column("parser", sa.String(120), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_decisions", JSON, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_resumes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resumes")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_resumes_storage_key")),
    )
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"])
    # One default resume per user.
    op.create_index(
        "uq_resumes_user_default",
        "resumes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
        sqlite_where=sa.text("is_default = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_resumes_user_default", table_name="resumes")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_table("resumes")
