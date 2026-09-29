"""jobs, job sources, matches and search runs

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

EMPLOYMENT = ("full_time", "part_time", "contract", "internship", "temporary", "freelance")


def _enum(name: str, length: int, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=length)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _user_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["user_id"], ["users.id"], name=op.f(f"fk_{table}_user_id_users"), ondelete="CASCADE"
    )


def upgrade() -> None:
    op.add_column(
        "job_preferences",
        sa.Column("match_weights", JSON, nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "job_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("board", sa.String(80), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_count", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        *_timestamps(),
        _user_fk("job_sources"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_sources")),
        sa.UniqueConstraint(
            "user_id", "platform", "board", name=op.f("uq_job_sources_user_id_platform_board")
        ),
    )
    op.create_index(op.f("ix_job_sources_user_id"), "job_sources", ["user_id"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("board", sa.String(80), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column(
            "workplace",
            _enum("workplacetype", 16, "remote", "hybrid", "onsite", "unknown"),
            nullable=False,
        ),
        sa.Column("employment_type", _enum("employmenttype", 16, *EMPLOYMENT), nullable=True),
        sa.Column("department", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("application_url", sa.String(1000), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(3), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(400), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("facts", JSON, nullable=False),
        sa.Column("raw", JSON, nullable=False),
        sa.Column(
            "analysis_status",
            _enum("analysisstatus", 16, "none", "pending", "processing", "done", "failed"),
            nullable=False,
        ),
        sa.Column("analysis", JSON, nullable=True),
        sa.Column("analysis_error", sa.String(300), nullable=True),
        sa.Column("analysis_prompt_version", sa.String(64), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("platform", "external_id", name=op.f("uq_jobs_platform_external_id")),
    )
    op.create_index("ix_jobs_board", "jobs", ["platform", "board"])
    op.create_index(op.f("ix_jobs_dedupe_key"), "jobs", ["dedupe_key"])

    op.create_table(
        "job_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("skills_match", sa.Integer(), nullable=False),
        sa.Column("experience_match", sa.Integer(), nullable=False),
        sa.Column("location_match", sa.Integer(), nullable=False),
        sa.Column("salary_match", sa.Integer(), nullable=False),
        sa.Column("preference_match", sa.Integer(), nullable=False),
        sa.Column("other_match", sa.Integer(), nullable=False),
        sa.Column("overall_match", sa.Integer(), nullable=False),
        sa.Column("reasons", JSON, nullable=False),
        sa.Column("missing_requirements", JSON, nullable=False),
        sa.Column("concerns", JSON, nullable=False),
        sa.Column("notes", JSON, nullable=False),
        sa.Column("excluded_reason", sa.String(300), nullable=True),
        sa.Column("recommended_resume_id", sa.Uuid(), nullable=True),
        sa.Column("resume_reason", sa.String(300), nullable=True),
        sa.Column("status", _enum("jobmatchstatus", 16, "new", "saved", "skipped"), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        _user_fk("job_matches"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_job_matches_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recommended_resume_id"],
            ["resumes.id"],
            name=op.f("fk_job_matches_recommended_resume_id_resumes"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_matches")),
        sa.UniqueConstraint("user_id", "job_id", name=op.f("uq_job_matches_user_id_job_id")),
    )
    op.create_index(op.f("ix_job_matches_user_id"), "job_matches", ["user_id"])
    op.create_index("ix_job_matches_user_overall", "job_matches", ["user_id", "overall_match"])

    op.create_table(
        "search_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            _enum("searchrunstatus", 16, "queued", "running", "succeeded", "failed"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sources_total", sa.Integer(), nullable=False),
        sa.Column("sources_done", sa.Integer(), nullable=False),
        sa.Column("jobs_fetched", sa.Integer(), nullable=False),
        sa.Column("jobs_new", sa.Integer(), nullable=False),
        sa.Column("jobs_closed", sa.Integer(), nullable=False),
        sa.Column("matches", sa.Integer(), nullable=False),
        sa.Column("source_errors", JSON, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        *_timestamps(),
        _user_fk("search_runs"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_runs")),
    )
    op.create_index(op.f("ix_search_runs_user_id"), "search_runs", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_search_runs_user_id"), table_name="search_runs")
    op.drop_table("search_runs")
    op.drop_index("ix_job_matches_user_overall", table_name="job_matches")
    op.drop_index(op.f("ix_job_matches_user_id"), table_name="job_matches")
    op.drop_table("job_matches")
    op.drop_index(op.f("ix_jobs_dedupe_key"), table_name="jobs")
    op.drop_index("ix_jobs_board", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_job_sources_user_id"), table_name="job_sources")
    op.drop_table("job_sources")
    op.drop_column("job_preferences", "match_weights")
