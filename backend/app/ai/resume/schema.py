"""The structured resume the AI returns (also the stored `resumes.parsed_data` shape).

Every field is required (nullable instead of defaulted) so the JSON schema works with
providers' strict structured-output modes. Each list item carries `evidence`: a line
copied from the resume, which `grounding.ground()` verifies against the source text.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResumeLink(_Strict):
    kind: Literal["linkedin", "github", "portfolio", "other"]
    url: str


class ResumeSkill(_Strict):
    name: str
    years: float | None = Field(description="Only if the resume states years for this skill")
    evidence: str


class ResumeExperience(_Strict):
    title: str | None
    company: str | None
    location: str | None
    start: str | None = Field(description="YYYY-MM or YYYY")
    end: str | None = Field(description="YYYY-MM or YYYY; null when current")
    is_current: bool
    description: str | None
    technologies: list[str]
    evidence: str


class ResumeEducation(_Strict):
    institution: str | None
    degree: str | None
    field_of_study: str | None
    start_year: int | None
    end_year: int | None
    grade: str | None
    evidence: str


class ResumeCertification(_Strict):
    name: str
    issuer: str | None
    year: int | None
    evidence: str


class ParsedResume(_Strict):
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    headline: str | None
    summary: str | None
    total_years_experience: float | None
    total_years_evidence: str | None
    links: list[ResumeLink]
    skills: list[ResumeSkill]
    experiences: list[ResumeExperience]
    education: list[ResumeEducation]
    certifications: list[ResumeCertification]
