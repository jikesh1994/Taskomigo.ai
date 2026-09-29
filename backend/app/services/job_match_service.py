"""Score jobs against one user's profile and preferences, and store the results.

Deterministic (no AI per job), so matching every job on every search costs nothing and
the same inputs always give the same score and explanation.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.jobs.extract import JobFacts, extract_facts
from app.jobs.matching import (
    JobInput,
    ResumeCandidate,
    UserFacts,
    match_job,
    norm,
    normalize_weights,
    recommend_resume,
)
from app.jobs.skills_vocab import SKILLS, canonical_skill
from app.models.enums import EmploymentType, RemotePreference, ResumeParseStatus
from app.models.experience import Experience
from app.models.job import Job, JobMatch
from app.repositories.job_repository import JobRepository
from app.repositories.preferences_repository import PreferencesRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.resume_repository import ResumeRepository

_VOCAB = frozenset(norm(name) for name in SKILLS)


@dataclass(frozen=True)
class MatchContext:
    user: UserFacts
    weights: dict[str, int]
    min_score: int
    resumes: list[ResumeCandidate]
    # Profile skills the vocabulary doesn't know; job facts are re-read with these.
    extra_skills: tuple[str, ...]


def total_years(experiences: Sequence[Experience], today: date | None = None) -> float | None:
    """Years covered by work history, counting overlapping jobs once."""
    today = today or date.today()
    spans = sorted(
        (e.start_date, e.end_date or today)
        for e in experiences
        if (e.end_date or today) > e.start_date
    )
    if not spans:
        return None
    days = 0
    current_start, current_end = spans[0]
    for start, end in spans[1:]:
        if start > current_end:
            days += (current_end - current_start).days
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    days += (current_end - current_start).days
    return round(days / 365.25, 1)


async def load_context(session: AsyncSession, user_id: uuid.UUID) -> MatchContext:
    profile = await ProfileRepository(session).get_for_user(user_id, with_children=True)
    preferences = await PreferencesRepository(session).get_for_user(user_id)

    skills: dict[str, tuple[str, float | None]] = {}
    extra: list[str] = []
    years: float | None = None
    if profile is not None:
        for skill in profile.skills:
            name = canonical_skill(skill.name)
            skills[norm(name)] = (name, skill.years)
            if norm(name) not in _VOCAB:
                extra.append(name)
        # Technologies used in past roles count too (without a years figure).
        for experience in profile.experiences:
            for tech in experience.technologies:
                name = canonical_skill(tech)
                skills.setdefault(norm(name), (name, None))
        years = profile.years_of_experience
        if years is None:
            years = total_years(profile.experiences)

    user = UserFacts(
        skills=skills,
        total_years=years,
        preferred_titles=tuple(profile.preferred_titles) if profile else (),
        preferred_locations=tuple(profile.preferred_locations) if profile else (),
        remote_preference=profile.remote_preference if profile else RemotePreference.ANY,
        willing_to_relocate=profile.willing_to_relocate if profile else None,
        expected_salary_min=profile.expected_salary_min if profile else None,
        currency=profile.currency if profile else None,
        sponsorship_required=profile.sponsorship_required if profile else None,
        remote_only=preferences.remote_only if preferences else False,
        min_salary=preferences.min_salary if preferences else None,
        salary_currency=preferences.salary_currency if preferences else None,
        employment_types=frozenset(
            EmploymentType(t) for t in (preferences.employment_types if preferences else [])
        ),
        keywords=tuple(preferences.keywords) if preferences else (),
        excluded_companies=tuple(preferences.excluded_companies) if preferences else (),
        excluded_industries=tuple(preferences.excluded_industries) if preferences else (),
    )

    resumes = [
        ResumeCandidate(
            id=str(r.id),
            name=r.name,
            is_default=r.is_default,
            skills=frozenset(
                norm(canonical_skill(s.get("name", "")))
                for s in (r.parsed_data or {}).get("skills", [])
            ),
        )
        for r in await ResumeRepository(session).list_for_user(user_id)
        if r.parse_status is ResumeParseStatus.PARSED
    ]
    return MatchContext(
        user=user,
        weights=normalize_weights(preferences.match_weights if preferences else None),
        min_score=preferences.min_match_score if preferences else 60,
        resumes=resumes,
        extra_skills=tuple(dict.fromkeys(extra)),
    )


def job_facts(job: Job, extra_skills: tuple[str, ...] = ()) -> JobFacts:
    if not extra_skills and job.facts:
        return JobFacts.from_dict(job.facts)
    return extract_facts(
        title=job.title,
        description=job.description,
        location=job.location,
        workplace=job.workplace,
        employment_type=job.employment_type,
        salary=(job.salary_min, job.salary_max, job.salary_currency),
        extra_skills=extra_skills,
    )


def _pick_canonical(group: list[Job]) -> Job:
    """One posting per dedupe key: the most recently posted/updated."""
    return max(group, key=lambda j: (j.posted_at or j.first_seen_at, str(j.id)))


class JobMatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = JobRepository(session)

    async def match_jobs(self, user_id: uuid.UUID, jobs: Sequence[Job]) -> int:
        """Create or refresh the user's match for each job; returns how many were scored.

        Duplicate postings (same company, title and location on several boards) are
        scored once. The user's saved/skipped status is kept.
        """
        ctx = await load_context(self.session, user_id)
        existing = await self.repo.matches_by_job(user_id)
        groups: dict[str, list[Job]] = {}
        for job in jobs:
            groups.setdefault(job.dedupe_key, []).append(job)

        now = utc_now()
        duplicates: list[uuid.UUID] = []
        for group in groups.values():
            job = _pick_canonical(group)
            duplicates.extend(j.id for j in group if j.id != job.id and j.id in existing)
            facts = job_facts(job, ctx.extra_skills)
            result = match_job(
                JobInput(
                    company=job.company,
                    title=job.title,
                    location=job.location,
                    department=job.department,
                    description=job.description,
                    facts=facts,
                ),
                ctx.user,
                ctx.weights,
            )
            recommended = recommend_resume(facts, ctx.resumes)
            match = existing.get(job.id)
            if match is None:
                match = JobMatch(id=uuid.uuid4(), user_id=user_id, job_id=job.id)
                self.repo.add(match)
            match.skills_match = result.scores["skills"]
            match.experience_match = result.scores["experience"]
            match.location_match = result.scores["location"]
            match.salary_match = result.scores["salary"]
            match.preference_match = result.scores["preferences"]
            match.other_match = result.scores["other"]
            match.overall_match = result.overall
            match.reasons = result.reasons
            match.missing_requirements = result.missing
            match.concerns = result.concerns
            match.notes = result.notes
            match.excluded_reason = result.excluded_reason
            match.recommended_resume_id = uuid.UUID(recommended[0]) if recommended else None
            match.resume_reason = recommended[1] if recommended else None
            match.computed_at = now
        await self.repo.delete_matches(user_id, duplicates)
        return len(groups)

    async def rematch(self, user_id: uuid.UUID) -> int:
        """Re-score every open job from the user's sources (after profile/preference edits)."""
        sources = await self.repo.list_sources(user_id)
        jobs = await self.repo.active_jobs_for_boards([(s.platform, s.board) for s in sources])
        count = await self.match_jobs(user_id, jobs)
        await self.session.commit()
        return count
