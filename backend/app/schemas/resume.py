from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.ai.resume.schema import ParsedResume
from app.models.enums import ResumeFileType, ResumeParseStatus
from app.schemas.common import ORMModel, UtcDatetime

ResumeName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ResumeRead(ORMModel):
    id: uuid.UUID
    name: str
    original_filename: str
    file_type: ResumeFileType
    size_bytes: int
    is_default: bool
    parse_status: ResumeParseStatus
    parse_error_code: str | None
    parse_error: str | None = Field(description="User-safe explanation when parse_status=failed")
    parser: str | None
    parsed_at: UtcDatetime | None
    created_at: UtcDatetime
    pending_review: int = Field(0, description="Open review items (conflicts and additions)")


class ResumeDetail(ResumeRead):
    parsed: ParsedResume | None


class ResumeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ResumeName | None = None
    is_default: Literal[True] | None = Field(
        None, description="Make this the default resume (the previous default is unset)"
    )


# ------------------------------------------------------------------ review

ReviewKind = Literal["conflict", "addition"]
ReviewAction = Literal["use_resume", "keep_profile", "add", "skip"]


class ReviewItem(BaseModel):
    id: str
    kind: ReviewKind
    field: str = Field(
        examples=["skill.years", "years_of_experience", "skill.add", "experience.add"]
    )
    label: str = Field(examples=["Python experience"])
    question: str = Field(
        examples=["Profile and resume contain different experience values. Which should be used?"]
    )
    profile_value: str | None
    resume_value: str
    evidence: str | None = Field(description="The resume line this came from")


class ResumeReview(BaseModel):
    resume_id: uuid.UUID
    items: list[ReviewItem]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    action: ReviewAction


class ReviewApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[ReviewDecision] = Field(min_length=1, max_length=200)


class ReviewApplyResult(BaseModel):
    applied: int
    skipped: int
    errors: list[str]
    review: ResumeReview
