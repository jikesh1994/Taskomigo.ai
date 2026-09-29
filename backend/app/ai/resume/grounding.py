"""Enforce "never invent information" on AI-parsed resumes.

Every value the model returns must be traceable to the resume text. Values that can't
be found are removed (or the whole entry is dropped), and each removal is reported so
it can be logged and, if needed, surfaced. The prompt asks for grounded output; this
module doesn't trust that it got it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai.resume.schema import (
    ParsedResume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeLink,
    ResumeSkill,
)

_NON_WORD = re.compile(r"[^\w+#]+", re.UNICODE)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_YEAR = re.compile(r"(?:19|20)\d{2}")


def _norm(value: str) -> str:
    """Case-, punctuation- and whitespace-insensitive form (keeps + and # for C++/C#)."""
    return " ".join(_NON_WORD.sub(" ", value.casefold()).split())


@dataclass
class _Source:
    text: str
    normalized: str = field(init=False)
    tokens: frozenset[str] = field(init=False)
    digits: str = field(init=False)

    def __post_init__(self) -> None:
        self.normalized = f" {_norm(self.text)} "
        self.tokens = frozenset(self.normalized.split())
        self.digits = re.sub(r"\D", "", self.text)

    def contains(self, value: str | None) -> bool:
        """Whole-word match of `value` somewhere in the resume."""
        if not value or not value.strip():
            return False
        needle = _norm(value)
        return bool(needle) and f" {needle} " in self.normalized

    def supports(self, evidence: str | None) -> bool:
        """The evidence line is in the resume (allowing minor reformatting by the model)."""
        if not evidence or not _norm(evidence):
            return False
        if self.contains(evidence):
            return True
        words = _norm(evidence).split()
        return len(words) >= 3 and sum(w in self.tokens for w in words) / len(words) >= 0.9


@dataclass
class GroundingResult:
    resume: ParsedResume
    removed: list[str]


def ground(parsed: ParsedResume, text: str) -> GroundingResult:
    source = _Source(text)
    removed: list[str] = []

    def keep(value: str | None, label: str) -> str | None:
        if value is None or source.contains(value):
            return value
        removed.append(label)
        return None

    def number_in(
        value: float | int | None, evidence: str | None, label: str
    ) -> float | int | None:
        if value is None:
            return None
        numbers = {float(n) for n in _NUMBER.findall(evidence or "")}
        if float(value) in numbers and source.supports(evidence):
            return value
        removed.append(label)
        return None

    def date_ok(value: str | None, label: str) -> str | None:
        if value is None:
            return None
        year = _YEAR.search(value)
        if year and source.contains(year.group()):
            return value
        removed.append(label)
        return None

    phone = parsed.phone
    if phone and re.sub(r"\D", "", phone) not in source.digits:
        removed.append("phone")
        phone = None

    summary = parsed.summary
    if summary and not source.supports(summary):
        removed.append("summary")
        summary = None

    links: list[ResumeLink] = []
    for link in parsed.links:
        if _link_in(link, source):
            links.append(link)
        else:
            removed.append(f"link {link.url}")

    skills: list[ResumeSkill] = []
    for skill in parsed.skills:
        if not source.contains(skill.name):
            removed.append(f"skill {skill.name!r}")
            continue
        years = number_in(skill.years, skill.evidence, f"years for skill {skill.name!r}")
        skills.append(skill.model_copy(update={"years": years}))

    experiences: list[ResumeExperience] = []
    for exp in parsed.experiences:
        label = f"experience {exp.title!r} at {exp.company!r}"
        title = keep(exp.title, f"{label}: title")
        company = keep(exp.company, f"{label}: company")
        if not (title or company) or not source.supports(exp.evidence):
            removed.append(label)
            continue
        experiences.append(
            exp.model_copy(
                update={
                    "title": title,
                    "company": company,
                    "location": keep(exp.location, f"{label}: location"),
                    "start": date_ok(exp.start, f"{label}: start date"),
                    "end": None if exp.is_current else date_ok(exp.end, f"{label}: end date"),
                    "description": exp.description
                    if exp.description and source.supports(exp.description)
                    else None,
                    "technologies": [t for t in exp.technologies if source.contains(t)],
                }
            )
        )

    education: list[ResumeEducation] = []
    for edu in parsed.education:
        label = f"education {edu.degree!r} at {edu.institution!r}"
        institution = keep(edu.institution, f"{label}: institution")
        degree = keep(edu.degree, f"{label}: degree")
        if not (institution or degree) or not source.supports(edu.evidence):
            removed.append(label)
            continue
        education.append(
            edu.model_copy(
                update={
                    "institution": institution,
                    "degree": degree,
                    "field_of_study": keep(edu.field_of_study, f"{label}: field"),
                    "grade": keep(edu.grade, f"{label}: grade"),
                    "start_year": edu.start_year if _year_in(edu.start_year, source) else None,
                    "end_year": edu.end_year if _year_in(edu.end_year, source) else None,
                }
            )
        )

    certifications: list[ResumeCertification] = []
    for cert in parsed.certifications:
        if not source.contains(cert.name):
            removed.append(f"certification {cert.name!r}")
            continue
        issuer = keep(cert.issuer, f"certification issuer {cert.issuer!r}")
        year = cert.year if _year_in(cert.year, source) else None
        certifications.append(cert.model_copy(update={"issuer": issuer, "year": year}))

    total_years = number_in(
        parsed.total_years_experience, parsed.total_years_evidence, "total years of experience"
    )

    grounded = parsed.model_copy(
        update={
            "full_name": keep(parsed.full_name, "name"),
            "email": keep(parsed.email, "email"),
            "phone": phone,
            "location": keep(parsed.location, "location"),
            "headline": keep(parsed.headline, "headline"),
            "summary": summary,
            "total_years_experience": total_years,
            "total_years_evidence": parsed.total_years_evidence
            if total_years is not None
            else None,
            "links": links,
            "skills": skills,
            "experiences": experiences,
            "education": education,
            "certifications": certifications,
        }
    )
    return GroundingResult(resume=grounded, removed=removed)


def _link_in(link: ResumeLink, source: _Source) -> bool:
    bare = re.sub(r"^(https?://)?(www\.)?", "", link.url.strip(), flags=re.IGNORECASE).rstrip("/")
    return bool(bare) and bare.casefold() in source.text.casefold()


def _year_in(year: int | None, source: _Source) -> bool:
    return year is not None and source.contains(str(year))
