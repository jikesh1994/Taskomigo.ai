"""The schema the model fills in, kept deliberately flat.

Providers compile structured-output schemas into a decoding grammar, and every nullable
field (`anyOf: [T, null]`) multiplies its size: the full `ParsedResume` was rejected by
the Anthropic API as "compiled grammar is too large". So the model gets only strings,
booleans and lists (`""` means "not stated"), and `to_parsed()` converts the answer into
the typed `ParsedResume` the rest of the app uses.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.ai.resume.schema import (
    ParsedResume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeLink,
    ResumeSkill,
)


class _Flat(BaseModel):
    model_config = ConfigDict(extra="forbid")


class XLink(_Flat):
    kind: Literal["linkedin", "github", "portfolio", "other"]
    url: str


class XSkill(_Flat):
    name: str
    years: str  # digits as written, e.g. "7"; "" if not stated
    evidence: str


class XExperience(_Flat):
    title: str
    company: str
    location: str
    start: str  # "YYYY-MM" or "YYYY"
    end: str
    is_current: bool
    description: str
    technologies: list[str]
    evidence: str


class XEducation(_Flat):
    institution: str
    degree: str
    field_of_study: str
    start_year: str
    end_year: str
    grade: str
    evidence: str


class XCertification(_Flat):
    name: str
    issuer: str
    year: str
    evidence: str


class ResumeExtraction(_Flat):
    full_name: str
    email: str
    phone: str
    location: str
    headline: str
    summary: str
    total_years_experience: str
    total_years_evidence: str
    links: list[XLink]
    skills: list[XSkill]
    experiences: list[XExperience]
    education: list[XEducation]
    certifications: list[XCertification]


# ------------------------------------------------------------------ conversion

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_YEAR = re.compile(r"(?:19|20)\d{2}")


def _text(value: str) -> str | None:
    value = value.strip()
    return value or None


def _number(value: str) -> float | None:
    match = _NUMBER.search(value)
    return float(match.group()) if match else None


def _year(value: str) -> int | None:
    match = _YEAR.search(value)
    return int(match.group()) if match else None


def to_parsed(x: ResumeExtraction) -> ParsedResume:
    return ParsedResume(
        full_name=_text(x.full_name),
        email=_text(x.email),
        phone=_text(x.phone),
        location=_text(x.location),
        headline=_text(x.headline),
        summary=_text(x.summary),
        total_years_experience=_number(x.total_years_experience),
        total_years_evidence=_text(x.total_years_evidence),
        links=[
            ResumeLink(kind=link.kind, url=link.url.strip()) for link in x.links if link.url.strip()
        ],
        skills=[
            ResumeSkill(name=s.name.strip(), years=_number(s.years), evidence=s.evidence)
            for s in x.skills
            if s.name.strip()
        ],
        experiences=[
            ResumeExperience(
                title=_text(e.title),
                company=_text(e.company),
                location=_text(e.location),
                start=_text(e.start),
                end=None if e.is_current else _text(e.end),
                is_current=e.is_current,
                description=_text(e.description),
                technologies=[t.strip() for t in e.technologies if t.strip()],
                evidence=e.evidence,
            )
            for e in x.experiences
        ],
        education=[
            ResumeEducation(
                institution=_text(e.institution),
                degree=_text(e.degree),
                field_of_study=_text(e.field_of_study),
                start_year=_year(e.start_year),
                end_year=_year(e.end_year),
                grade=_text(e.grade),
                evidence=e.evidence,
            )
            for e in x.education
        ],
        certifications=[
            ResumeCertification(
                name=c.name.strip(), issuer=_text(c.issuer), year=_year(c.year), evidence=c.evidence
            )
            for c in x.certifications
            if c.name.strip()
        ],
    )


def from_parsed(p: ParsedResume) -> ResumeExtraction:
    """The inverse, for tests and the fake model server."""

    def s(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    return ResumeExtraction(
        full_name=s(p.full_name),
        email=s(p.email),
        phone=s(p.phone),
        location=s(p.location),
        headline=s(p.headline),
        summary=s(p.summary),
        total_years_experience=s(p.total_years_experience),
        total_years_evidence=s(p.total_years_evidence),
        links=[XLink(kind=link.kind, url=link.url) for link in p.links],
        skills=[XSkill(name=k.name, years=s(k.years), evidence=k.evidence) for k in p.skills],
        experiences=[
            XExperience(
                title=s(e.title),
                company=s(e.company),
                location=s(e.location),
                start=s(e.start),
                end=s(e.end),
                is_current=e.is_current,
                description=s(e.description),
                technologies=e.technologies,
                evidence=e.evidence,
            )
            for e in p.experiences
        ],
        education=[
            XEducation(
                institution=s(e.institution),
                degree=s(e.degree),
                field_of_study=s(e.field_of_study),
                start_year=s(e.start_year),
                end_year=s(e.end_year),
                grade=s(e.grade),
                evidence=e.evidence,
            )
            for e in p.education
        ],
        certifications=[
            XCertification(name=c.name, issuer=s(c.issuer), year=s(c.year), evidence=c.evidence)
            for c in p.certifications
        ],
    )
