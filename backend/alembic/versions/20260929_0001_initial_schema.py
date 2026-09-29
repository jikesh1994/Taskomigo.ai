"""initial schema: users, profiles, experience, education, skills, preferences,
refresh tokens, audit logs

Revision ID: 0001
Revises:
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=16)


def _profile_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["profile_id"],
        ["professional_profiles.id"],
        name=op.f(f"fk_{table}_profile_id_professional_profiles"),
        ondelete="CASCADE",
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("role", _enum("userrole", "user", "admin"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("result", _enum("auditresult", "success", "failure"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"])

    op.create_table(
        "job_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("keywords", JSON, nullable=False),
        sa.Column("employment_types", JSON, nullable=False),
        sa.Column("excluded_companies", JSON, nullable=False),
        sa.Column("excluded_industries", JSON, nullable=False),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(3), nullable=True),
        sa.Column("remote_only", sa.Boolean(), nullable=False),
        sa.Column("min_match_score", sa.Integer(), nullable=False),
        sa.Column("max_applications_per_day", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_browser_sessions", sa.Integer(), nullable=False),
        sa.Column("max_retries_per_application", sa.Integer(), nullable=False),
        sa.Column("auto_fill_enabled", sa.Boolean(), nullable=False),
        sa.Column("auto_answer_enabled", sa.Boolean(), nullable=False),
        sa.Column("review_before_submit", sa.Boolean(), nullable=False),
        sa.Column("auto_submit_enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_job_preferences_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_preferences")),
    )
    op.create_index(op.f("ix_job_preferences_user_id"), "job_preferences", ["user_id"], unique=True)

    op.create_table(
        "professional_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("headline", sa.String(200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("years_of_experience", sa.Float(), nullable=True),
        sa.Column("current_title", sa.String(200), nullable=True),
        sa.Column("current_company", sa.String(200), nullable=True),
        sa.Column("preferred_titles", JSON, nullable=False),
        sa.Column("preferred_locations", JSON, nullable=False),
        sa.Column(
            "remote_preference",
            _enum("remotepreference", "remote", "hybrid", "onsite", "any"),
            nullable=False,
        ),
        sa.Column("expected_salary_min", sa.Integer(), nullable=True),
        sa.Column("expected_salary_max", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("work_authorization", sa.String(255), nullable=True),
        sa.Column("sponsorship_required", sa.Boolean(), nullable=True),
        sa.Column("willing_to_relocate", sa.Boolean(), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_professional_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professional_profiles")),
    )
    op.create_index(
        op.f("ix_professional_profiles_user_id"), "professional_profiles", ["user_id"], unique=True
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_expires_at"), "refresh_tokens", ["expires_at"])
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"])
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"])

    op.create_table(
        "education",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("institution", sa.String(200), nullable=False),
        sa.Column("degree", sa.String(200), nullable=False),
        sa.Column("field_of_study", sa.String(200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
        *_timestamps(),
        _profile_fk("education"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_education")),
    )
    op.create_index(op.f("ix_education_profile_id"), "education", ["profile_id"])

    op.create_table(
        "experiences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column(
            "employment_type",
            _enum(
                "employmenttype",
                "full_time",
                "part_time",
                "contract",
                "internship",
                "temporary",
                "freelance",
            ),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("technologies", JSON, nullable=False),
        *_timestamps(),
        _profile_fk("experiences"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiences")),
    )
    op.create_index(op.f("ix_experiences_profile_id"), "experiences", ["profile_id"])

    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("years", sa.Float(), nullable=True),
        sa.Column(
            "proficiency",
            _enum("skillproficiency", "beginner", "intermediate", "advanced", "expert"),
            nullable=True,
        ),
        *_timestamps(),
        _profile_fk("skills"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint(
            "profile_id", "normalized_name", name=op.f("uq_skills_profile_id_normalized_name")
        ),
    )
    op.create_index(op.f("ix_skills_profile_id"), "skills", ["profile_id"])


def downgrade() -> None:
    for table in (
        "skills",
        "experiences",
        "education",
        "refresh_tokens",
        "professional_profiles",
        "job_preferences",
        "audit_logs",
        "users",
    ):
        op.drop_table(table)  # indexes and constraints are dropped with the table
