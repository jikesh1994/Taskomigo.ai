"""Enumerations shared by models and schemas."""

from __future__ import annotations

import enum


class UserRole(enum.StrEnum):
    USER = "user"
    ADMIN = "admin"


class RemotePreference(enum.StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


class SkillProficiency(enum.StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class EmploymentType(enum.StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    FREELANCE = "freelance"


class ResumeFileType(enum.StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class ResumeParseStatus(enum.StrEnum):
    PENDING = "pending"  # uploaded, waiting for a worker
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"  # see parse_error; the user can retry


class WorkplaceType(enum.StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class JobMatchStatus(enum.StrEnum):
    NEW = "new"
    SAVED = "saved"
    SKIPPED = "skipped"


class AnalysisStatus(enum.StrEnum):
    NONE = "none"
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class SearchRunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AuditResult(enum.StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
