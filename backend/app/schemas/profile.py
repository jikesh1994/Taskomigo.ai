from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.enums import EmploymentType, RemotePreference, SkillProficiency
from app.schemas.common import (
    CurrencyCode,
    ORMModel,
    PatchModel,
    ShortText,
    StringList,
    Text50,
    Text200,
    Text255,
    Text5000,
    Text10000,
    UrlStr,
    UtcDatetime,
)

Years = Annotated[float, Field(ge=0, le=60)]
Salary = Annotated[int, Field(ge=0, le=1_000_000_000)]
NoticeDays = Annotated[int, Field(ge=0, le=365)]


# --------------------------------------------------------------------------- invariants
# Shared by create/replace schemas and by services after merging a PATCH.


def validate_salary_expectation(lo: int | None, hi: int | None, currency: str | None) -> None:
    if lo is not None and hi is not None and lo > hi:
        raise ValueError("expected_salary_min must not exceed expected_salary_max")
    if (lo is not None or hi is not None) and currency is None:
        raise ValueError("currency is required when a salary expectation is provided")


def validate_experience_dates(start: date, end: date | None, is_current: bool) -> None:
    if is_current and end is not None:
        raise ValueError("A current position must not have an end_date")
    if end is not None and end < start:
        raise ValueError("end_date must not be before start_date")
    if start > date.today():
        raise ValueError("start_date must not be in the future")


def validate_education_dates(start: date | None, end: date | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_date must not be before start_date")


# --------------------------------------------------------------------------- profile


class ProfileReplace(BaseModel):
    """PUT /profile: every field is replaced; omitted fields reset to defaults."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "headline": "Senior Python Engineer",
                    "years_of_experience": 7,
                    "current_title": "Senior Backend Engineer",
                    "current_company": "Acme",
                    "preferred_titles": ["Senior Python Developer", "Backend Engineer"],
                    "preferred_locations": ["Bengaluru", "Remote"],
                    "remote_preference": "remote",
                    "expected_salary_min": 3000000,
                    "expected_salary_max": 4500000,
                    "currency": "INR",
                    "notice_period_days": 30,
                    "sponsorship_required": False,
                    "github_url": "https://github.com/ada",
                }
            ]
        },
    )

    headline: Text200 = None
    summary: Text5000 = None
    years_of_experience: Years | None = None
    current_title: Text200 = None
    current_company: Text200 = None
    preferred_titles: StringList = Field(default_factory=list)
    preferred_locations: StringList = Field(default_factory=list)
    remote_preference: RemotePreference = RemotePreference.ANY
    expected_salary_min: Salary | None = None
    expected_salary_max: Salary | None = None
    currency: CurrencyCode | None = None
    notice_period_days: NoticeDays | None = None
    work_authorization: Text255 = None
    sponsorship_required: bool | None = Field(
        default=None, description="null = unknown; the agent will ask instead of guessing"
    )
    willing_to_relocate: bool | None = None
    portfolio_url: UrlStr = None
    github_url: UrlStr = None
    linkedin_url: UrlStr = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        validate_salary_expectation(
            self.expected_salary_min, self.expected_salary_max, self.currency
        )
        return self


class ProfileUpdate(PatchModel):
    """PATCH /profile: only fields present in the body change."""

    non_nullable_fields = frozenset(
        {"preferred_titles", "preferred_locations", "remote_preference"}
    )

    headline: Text200 = None
    summary: Text5000 = None
    years_of_experience: Years | None = None
    current_title: Text200 = None
    current_company: Text200 = None
    preferred_titles: StringList | None = None
    preferred_locations: StringList | None = None
    remote_preference: RemotePreference | None = None
    expected_salary_min: Salary | None = None
    expected_salary_max: Salary | None = None
    currency: CurrencyCode | None = None
    notice_period_days: NoticeDays | None = None
    work_authorization: Text255 = None
    sponsorship_required: bool | None = None
    willing_to_relocate: bool | None = None
    portfolio_url: UrlStr = None
    github_url: UrlStr = None
    linkedin_url: UrlStr = None


# --------------------------------------------------------------------------- experience


class ExperienceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: ShortText
    title: ShortText
    location: Text200 = None
    employment_type: EmploymentType | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: Text10000 = None
    technologies: StringList = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        validate_experience_dates(self.start_date, self.end_date, self.is_current)
        return self


class ExperienceUpdate(PatchModel):
    non_nullable_fields = frozenset(
        {"company", "title", "start_date", "is_current", "technologies"}
    )

    company: ShortText | None = None
    title: ShortText | None = None
    location: Text200 = None
    employment_type: EmploymentType | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    description: Text10000 = None
    technologies: StringList | None = None


class ExperienceRead(ORMModel):
    id: uuid.UUID
    company: str
    title: str
    location: str | None
    employment_type: EmploymentType | None
    start_date: date
    end_date: date | None
    is_current: bool
    description: str | None
    technologies: list[str]


# --------------------------------------------------------------------------- education


class EducationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: ShortText
    degree: ShortText
    field_of_study: Text200 = None
    start_date: date | None = None
    end_date: date | None = None
    grade: Text50 = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        validate_education_dates(self.start_date, self.end_date)
        return self


class EducationUpdate(PatchModel):
    non_nullable_fields = frozenset({"institution", "degree"})

    institution: ShortText | None = None
    degree: ShortText | None = None
    field_of_study: Text200 = None
    start_date: date | None = None
    end_date: date | None = None
    grade: Text50 = None


class EducationRead(ORMModel):
    id: uuid.UUID
    institution: str
    degree: str
    field_of_study: str | None
    start_date: date | None
    end_date: date | None
    grade: str | None


# --------------------------------------------------------------------------- skills

SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: SkillName
    years: Years | None = None
    proficiency: SkillProficiency | None = None


class SkillUpdate(PatchModel):
    non_nullable_fields = frozenset({"name"})

    name: SkillName | None = None
    years: Years | None = None
    proficiency: SkillProficiency | None = None


class SkillRead(ORMModel):
    id: uuid.UUID
    name: str
    years: float | None
    proficiency: SkillProficiency | None


# --------------------------------------------------------------------------- aggregate


class ProfileRead(ORMModel):
    id: uuid.UUID
    headline: str | None
    summary: str | None
    years_of_experience: float | None
    current_title: str | None
    current_company: str | None
    preferred_titles: list[str]
    preferred_locations: list[str]
    remote_preference: RemotePreference
    expected_salary_min: int | None
    expected_salary_max: int | None
    currency: str | None
    notice_period_days: int | None
    work_authorization: str | None
    sponsorship_required: bool | None
    willing_to_relocate: bool | None
    portfolio_url: str | None
    github_url: str | None
    linkedin_url: str | None
    experiences: list[ExperienceRead]
    education: list[EducationRead]
    skills: list[SkillRead]
    updated_at: UtcDatetime
