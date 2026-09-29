"""Compare a parsed resume with the profile, and apply the user's decisions.

Two kinds of review item:
* conflict: both sides have a value and they differ. The user picks one
  ("Profile and resume contain different experience values. Which should be used?").
* addition: the resume has something the profile lacks. The user adds it or skips it.

Nothing from a resume reaches the profile without an explicit decision.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.resume.schema import ParsedResume, ResumeEducation, ResumeExperience
from app.core.exceptions import ConflictError
from app.models.education import Education
from app.models.enums import ResumeParseStatus
from app.models.experience import Experience
from app.models.profile import ProfessionalProfile
from app.models.resume import Resume
from app.models.skill import Skill
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.common import UrlStr
from app.schemas.profile import EducationCreate, ExperienceCreate, SkillCreate
from app.schemas.resume import ResumeReview, ReviewApplyResult, ReviewDecision, ReviewItem
from app.services.audit_service import AuditService, RequestContext
from app.services.profile_service import normalize_skill_name
from app.services.resume_service import ResumeService

CONFLICT_QUESTION = "Profile and resume contain different values. Which should be used?"
YEARS_QUESTION = "Profile and resume contain different experience values. Which should be used?"
ADD_QUESTION = "Your resume has this, but your profile doesn't. Add it to your profile?"


def _norm(value: str | None) -> str:
    return " ".join(re.sub(r"[^\w+#]+", " ", (value or "").casefold()).split())


def _item_id(field: str, key: str, value: str) -> str:
    return hashlib.sha256(f"{field}|{key}|{value}".encode()).hexdigest()[:20]


def _years(value: float | None) -> str:
    if value is None:
        return "not set"
    number = int(value) if float(value).is_integer() else value
    return f"{number} year" if number == 1 else f"{number} years"


def _parse_month(value: str | None) -> date | None:
    """ "2021-06" or "2021" → first day of that month/year."""
    if not value:
        return None
    match = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?", value.strip())
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2) or 1)
    return date(year, month, 1) if 1 <= month <= 12 else None


def _norm_url(url: str | None) -> str:
    return re.sub(r"^(https?://)?(www\.)?", "", (url or "").strip().casefold()).rstrip("/")


@dataclass
class _Candidate:
    item: ReviewItem
    # Applies the resume's value to the profile; raises ValueError/ValidationError if invalid.
    apply: Callable[[], None]


class ResumeReviewService:
    def __init__(self, session: AsyncSession, resumes: ResumeService) -> None:
        self.session = session
        self.resumes = resumes
        self.profiles = ProfileRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------ read

    async def review(self, user: User, resume_id: uuid.UUID) -> ResumeReview:
        resume = await self.resumes.get(user.id, resume_id)
        profile = await self._profile(user.id)
        return ResumeReview(
            resume_id=resume.id, items=[c.item for c in self._open(user, profile, resume)]
        )

    async def pending_counts(self, user: User, resumes: list[Resume]) -> dict[uuid.UUID, int]:
        if not any(r.parse_status is ResumeParseStatus.PARSED for r in resumes):
            return {}
        profile = await self._profile(user.id)
        return {r.id: len(self._open(user, profile, r)) for r in resumes}

    # ------------------------------------------------------------------ write

    async def apply(
        self, user: User, resume_id: uuid.UUID, decisions: list[ReviewDecision], ctx: RequestContext
    ) -> ReviewApplyResult:
        resume = await self.resumes.get(user.id, resume_id)
        if resume.parse_status is not ResumeParseStatus.PARSED:
            raise ConflictError("This resume hasn't been read yet.", code="resume_not_parsed")
        profile = await self._profile(user.id)
        candidates = {c.item.id: c for c in self._open(user, profile, resume)}

        recorded = dict(resume.review_decisions or {})
        applied = skipped = 0
        errors: list[str] = []
        for decision in decisions:
            candidate = candidates.get(decision.id)
            if candidate is None:
                continue  # already decided, or no longer relevant after other edits
            takes_resume = decision.action in ("use_resume", "add")
            if takes_resume:
                try:
                    candidate.apply()
                except (ValueError, ValidationError):
                    errors.append(
                        f"{candidate.item.label}: couldn't be added (incomplete or invalid)."
                    )
                    continue
                applied += 1
            else:
                skipped += 1
            recorded[decision.id] = decision.action

        resume.review_decisions = recorded  # reassign: in-place JSON edits aren't tracked
        self.audit.record(
            "resume.review_apply",
            user_id=user.id,
            entity="resume",
            entity_id=resume.id,
            context=ctx,
            details={"applied": applied, "skipped": skipped, "errors": len(errors)},
        )
        await self.session.commit()
        refreshed = await self._profile(user.id)
        remaining = [c.item for c in self._open(user, refreshed, resume)]
        return ReviewApplyResult(
            applied=applied,
            skipped=skipped,
            errors=errors,
            review=ResumeReview(resume_id=resume.id, items=remaining),
        )

    # ------------------------------------------------------------------ detection

    async def _profile(self, user_id: uuid.UUID) -> ProfessionalProfile:
        profile = await self.profiles.get_for_user(user_id, with_children=True)
        if profile is None:
            profile = ProfessionalProfile(id=uuid.uuid4(), user_id=user_id)
            self.profiles.add(profile)
            await self.session.flush()
            profile = await self.profiles.get_for_user(user_id, with_children=True)
        assert profile is not None
        return profile

    def _open(self, user: User, profile: ProfessionalProfile, resume: Resume) -> list[_Candidate]:
        if resume.parse_status is not ResumeParseStatus.PARSED or not resume.parsed_data:
            return []
        parsed = ParsedResume.model_validate(resume.parsed_data)
        decided = resume.review_decisions or {}
        candidates = [
            *self._scalars(user, profile, parsed),
            *self._skills(profile, parsed),
            *self._experiences(profile, parsed),
            *self._education(profile, parsed),
        ]
        return [c for c in candidates if c.item.id not in decided]

    def _scalars(
        self, user: User, profile: ProfessionalProfile, parsed: ParsedResume
    ) -> list[_Candidate]:
        out: list[_Candidate] = []

        def compare(
            field: str,
            label: str,
            current: Any,
            proposed: Any,
            setter: Callable[[], None],
            *,
            shown: Callable[[Any], str] = str,
            same: Callable[[Any, Any], bool] = lambda a, b: _norm(str(a)) == _norm(str(b)),
            evidence: str | None = None,
            question: str = CONFLICT_QUESTION,
        ) -> None:
            if proposed is None or (isinstance(proposed, str) and not proposed.strip()):
                return
            if current is None or (isinstance(current, str) and not current.strip()):
                kind, q = "addition", ADD_QUESTION
            elif same(current, proposed):
                return
            else:
                kind, q = "conflict", question
            value = shown(proposed)
            out.append(
                _Candidate(
                    ReviewItem(
                        id=_item_id(field, "", value),
                        kind=kind,
                        field=field,
                        label=label,
                        question=q,
                        profile_value=None if kind == "addition" else shown(current),
                        resume_value=value,
                        evidence=evidence,
                    ),
                    setter,
                )
            )

        total = parsed.total_years_experience
        compare(
            "years_of_experience",
            "Total years of experience",
            profile.years_of_experience,
            total,
            lambda: setattr(profile, "years_of_experience", _checked_years(total)),
            shown=_years,
            same=lambda a, b: abs(float(a) - float(b)) < 0.05,
            evidence=parsed.total_years_evidence,
            question=YEARS_QUESTION,
        )
        current_role = next((e for e in parsed.experiences if e.is_current), None)
        if current_role is not None:
            compare(
                "current_title",
                "Current job title",
                profile.current_title,
                current_role.title,
                lambda: setattr(profile, "current_title", (current_role.title or "")[:200]),
                evidence=current_role.evidence,
            )
            compare(
                "current_company",
                "Current company",
                profile.current_company,
                current_role.company,
                lambda: setattr(profile, "current_company", (current_role.company or "")[:200]),
                evidence=current_role.evidence,
            )
        compare(
            "headline",
            "Professional headline",
            profile.headline,
            parsed.headline,
            lambda: setattr(profile, "headline", (parsed.headline or "")[:200]),
        )
        if not profile.summary and parsed.summary:
            compare(
                "summary",
                "Professional summary",
                profile.summary,
                parsed.summary,
                lambda: setattr(profile, "summary", (parsed.summary or "")[:5000]),
            )
        if not user.phone and parsed.phone:
            compare(
                "phone", "Phone", user.phone, parsed.phone, lambda: _set_phone(user, parsed.phone)
            )
        for kind, attr, label in (
            ("linkedin", "linkedin_url", "LinkedIn"),
            ("github", "github_url", "GitHub"),
            ("portfolio", "portfolio_url", "Portfolio"),
        ):
            link = next((lnk for lnk in parsed.links if lnk.kind == kind), None)
            if link is not None:
                compare(
                    f"link.{kind}",
                    label,
                    getattr(profile, attr),
                    link.url,
                    lambda attr=attr, url=link.url: setattr(profile, attr, _checked_url(url)),
                    same=lambda a, b: _norm_url(a) == _norm_url(b),
                )
        return out

    def _skills(self, profile: ProfessionalProfile, parsed: ParsedResume) -> list[_Candidate]:
        existing = {s.normalized_name: s for s in profile.skills}
        out: list[_Candidate] = []
        seen: set[str] = set()
        for skill in parsed.skills:
            key = normalize_skill_name(skill.name)
            if not key or key in seen:
                continue
            seen.add(key)
            mine = existing.get(key)
            if mine is None:
                value = (
                    skill.name if skill.years is None else f"{skill.name} ({_years(skill.years)})"
                )
                out.append(
                    _Candidate(
                        ReviewItem(
                            id=_item_id("skill.add", key, value),
                            kind="addition",
                            field="skill.add",
                            label=f"Skill: {skill.name}",
                            question=ADD_QUESTION,
                            profile_value=None,
                            resume_value=value,
                            evidence=skill.evidence,
                        ),
                        lambda skill=skill, key=key: self._add_skill(
                            profile, skill.name, skill.years, key
                        ),
                    )
                )
            elif skill.years is not None and (
                mine.years is None or abs(mine.years - skill.years) >= 0.05
            ):
                kind = "addition" if mine.years is None else "conflict"
                out.append(
                    _Candidate(
                        ReviewItem(
                            id=_item_id("skill.years", key, str(skill.years)),
                            kind=kind,
                            field="skill.years",
                            label=f"{mine.name} experience",
                            question=YEARS_QUESTION if kind == "conflict" else ADD_QUESTION,
                            profile_value=_years(mine.years) if kind == "conflict" else None,
                            resume_value=_years(skill.years),
                            evidence=skill.evidence,
                        ),
                        lambda mine=mine, years=skill.years: setattr(
                            mine, "years", _checked_years(years)
                        ),
                    )
                )
        return out

    def _experiences(self, profile: ProfessionalProfile, parsed: ParsedResume) -> list[_Candidate]:
        existing = {(_norm(e.company), _norm(e.title)) for e in profile.experiences}
        out: list[_Candidate] = []
        for exp in parsed.experiences:
            if not (exp.title and exp.company and _parse_month(exp.start)):
                continue  # can't form a complete profile entry
            if (_norm(exp.company), _norm(exp.title)) in existing:
                continue
            period = f"{exp.start} to {'present' if exp.is_current else exp.end or '?'}"
            value = f"{exp.title} at {exp.company} ({period})"
            out.append(
                _Candidate(
                    ReviewItem(
                        id=_item_id("experience.add", _norm(exp.company + exp.title), value),
                        kind="addition",
                        field="experience.add",
                        label=f"Experience: {exp.title} at {exp.company}",
                        question=ADD_QUESTION,
                        profile_value=None,
                        resume_value=value,
                        evidence=exp.evidence,
                    ),
                    lambda exp=exp: self._add_experience(profile, exp),
                )
            )
        return out

    def _education(self, profile: ProfessionalProfile, parsed: ParsedResume) -> list[_Candidate]:
        existing = {(_norm(e.institution), _norm(e.degree)) for e in profile.education}
        out: list[_Candidate] = []
        for edu in parsed.education:
            if not (edu.institution and edu.degree):
                continue
            if (_norm(edu.institution), _norm(edu.degree)) in existing:
                continue
            subject = f", {edu.field_of_study}" if edu.field_of_study else ""
            value = f"{edu.degree}{subject}, {edu.institution}" + (
                f" ({edu.end_year})" if edu.end_year else ""
            )
            out.append(
                _Candidate(
                    ReviewItem(
                        id=_item_id("education.add", _norm(edu.institution + edu.degree), value),
                        kind="addition",
                        field="education.add",
                        label=f"Education: {edu.degree}",
                        question=ADD_QUESTION,
                        profile_value=None,
                        resume_value=value,
                        evidence=edu.evidence,
                    ),
                    lambda edu=edu: self._add_education(profile, edu),
                )
            )
        return out

    # ------------------------------------------------------------------ appliers
    # Each goes through the same Pydantic schemas as the profile API, so resume data
    # can never bypass the profile's validation rules.

    def _add_skill(
        self, profile: ProfessionalProfile, name: str, years: float | None, key: str
    ) -> None:
        data = SkillCreate(name=name, years=years)
        self.profiles.add(Skill(profile_id=profile.id, normalized_name=key, **data.model_dump()))

    def _add_experience(self, profile: ProfessionalProfile, exp: ResumeExperience) -> None:
        data = ExperienceCreate(
            company=exp.company or "",
            title=exp.title or "",
            location=exp.location,
            start_date=_parse_month(exp.start),  # type: ignore[arg-type]
            end_date=None if exp.is_current else _parse_month(exp.end),
            is_current=exp.is_current,
            description=exp.description,
            technologies=exp.technologies,
        )
        self.profiles.add(Experience(profile_id=profile.id, **data.model_dump()))

    def _add_education(self, profile: ProfessionalProfile, edu: ResumeEducation) -> None:
        data = EducationCreate(
            institution=edu.institution or "",
            degree=edu.degree or "",
            field_of_study=edu.field_of_study,
            start_date=date(edu.start_year, 1, 1) if edu.start_year else None,
            end_date=date(edu.end_year, 1, 1) if edu.end_year else None,
            grade=edu.grade,
        )
        self.profiles.add(Education(profile_id=profile.id, **data.model_dump()))


def _checked_years(value: float | None) -> float:
    if value is None or not 0 <= value <= 60:
        raise ValueError("years out of range")
    return float(value)


def _checked_url(value: str) -> str:
    from pydantic import TypeAdapter

    url = value if value.startswith(("http://", "https://")) else f"https://{value}"
    validated = TypeAdapter(UrlStr).validate_python(url)
    if validated is None:
        raise ValueError("empty url")
    return validated


def _set_phone(user: User, phone: str | None) -> None:
    from app.schemas.user import UserUpdate

    user.phone = UserUpdate(phone=phone).phone
