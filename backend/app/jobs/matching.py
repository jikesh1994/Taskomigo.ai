"""Deterministic, explainable job matching.

Each job gets six component scores (0-100), a weighted overall score, human-readable
reasons it was included, the requirements the user is missing, and concerns. Hard
filters (exclusions, remote-only, minimum salary, ...) remove obvious mismatches.

The score explains *fit against the user's own criteria*. It is not, and must never be
presented as, a prediction of interviews or hiring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.jobs.extract import JobFacts
from app.jobs.types import WorkplaceType
from app.models.enums import EmploymentType, RemotePreference

COMPONENTS = ("skills", "experience", "location", "salary", "preferences", "other")
DEFAULT_WEIGHTS: dict[str, int] = {
    "skills": 40, "experience": 20, "location": 10, "salary": 10, "preferences": 10, "other": 10,
}  # fmt: skip

_WORD = re.compile(r"[a-z0-9+#]+")
_STOP = {"a", "an", "and", "of", "the", "for", "to", "in", "at", "i", "ii", "iii", "iv", "sr", "jr"}


def norm(value: str | None) -> str:
    return " ".join(_WORD.findall((value or "").casefold()))


# Role-family synonyms so "Software Developer" and "Backend Engineer" share "engineer".
_SYNONYMS = {
    "developer": "engineer", "programmer": "engineer", "dev": "engineer", "sde": "engineer",
    "swe": "engineer", "engineering": "engineer", "back": "backend", "front": "frontend",
    "fullstack": "full-stack", "mgr": "manager", "ml": "machine", "ai": "machine",
}  # fmt: skip


def _tokens(value: str | None) -> set[str]:
    words = _WORD.findall((value or "").casefold().replace("full stack", "fullstack"))
    return {_SYNONYMS.get(t, t) for t in words if t not in _STOP}


def title_similarity(target: str, title: str) -> float:
    """Share of the target title's words (after synonyms) that appear in the job title."""
    wanted = _tokens(target)
    return len(wanted & _tokens(title)) / len(wanted) if wanted else 0.0


def _years(value: float, plus: bool = False) -> str:
    number = int(value) if float(value).is_integer() else value
    unit = "year" if number == 1 and not plus else "years"
    return f"{number}{'+' if plus else ''} {unit}"


def _money(amount: int, currency: str) -> str:
    if currency == "INR" and amount >= 100_000:
        return f"₹{amount / 100_000:g} lakh"
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, f"{currency} ")
    return f"{symbol}{amount:,}"


@dataclass(frozen=True)
class UserFacts:
    skills: dict[str, tuple[str, float | None]]  # normalized name → (display name, years)
    total_years: float | None = None
    preferred_titles: tuple[str, ...] = ()
    preferred_locations: tuple[str, ...] = ()
    remote_preference: RemotePreference = RemotePreference.ANY
    remote_only: bool = False
    willing_to_relocate: bool | None = None
    expected_salary_min: int | None = None
    currency: str | None = None
    min_salary: int | None = None
    salary_currency: str | None = None
    sponsorship_required: bool | None = None
    employment_types: frozenset[EmploymentType] = frozenset()
    keywords: tuple[str, ...] = ()
    excluded_companies: tuple[str, ...] = ()
    excluded_industries: tuple[str, ...] = ()


@dataclass(frozen=True)
class JobInput:
    company: str
    title: str
    location: str | None
    department: str | None
    description: str
    facts: JobFacts


@dataclass
class MatchResult:
    scores: dict[str, int]
    overall: int
    reasons: list[str] = field(default_factory=list)  # why it was included
    missing: list[str] = field(default_factory=list)  # requirements the user lacks
    concerns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # neutral facts ("Salary not listed")
    excluded_reason: str | None = None


def normalize_weights(weights: dict[str, int] | None) -> dict[str, int]:
    merged = {**DEFAULT_WEIGHTS, **{k: v for k, v in (weights or {}).items() if k in COMPONENTS}}
    return merged if sum(merged.values()) > 0 else dict(DEFAULT_WEIGHTS)


def match_job(job: JobInput, user: UserFacts, weights: dict[str, int] | None = None) -> MatchResult:
    result = MatchResult(scores={}, overall=0)
    f = job.facts
    result.scores["skills"] = _skills(f, user, result)
    result.scores["experience"] = _experience(f, user, result)
    result.scores["location"] = _location(job, user, result)
    result.scores["salary"] = _salary(f, user, result)
    result.scores["preferences"] = _preferences(job, user, result)
    result.scores["other"] = _other(f, user, result)
    w = normalize_weights(weights)
    result.overall = round(sum(result.scores[c] * w[c] for c in COMPONENTS) / sum(w.values()))
    result.excluded_reason = _exclusion(job, user)
    return result


# ------------------------------------------------------------------ components


def _skills(f: JobFacts, user: UserFacts, r: MatchResult) -> int:
    def mine(skill: str) -> tuple[str, float | None] | None:
        return user.skills.get(norm(skill))

    required, preferred = f.required_skills, f.preferred_skills
    if not required and not preferred:
        r.notes.append("No specific skills listed")
        return 50
    matched = [s for s in required if mine(s)]
    for skill in matched[:6]:
        _, years = mine(skill)  # type: ignore[misc]
        suffix = f" (you have {_years(years)})" if years else ""
        r.reasons.append(f"{skill} required: on your profile{suffix}")
    for skill in [s for s in required if not mine(s)]:
        r.missing.append(skill)
    pref_matched = [s for s in preferred if mine(s)]
    if pref_matched:
        r.reasons.append(f"Nice-to-have skills you have: {', '.join(pref_matched[:4])}")
    if required:
        score = 100 * len(matched) / len(required)
        if preferred:
            score += 10 * len(pref_matched) / len(preferred)
    else:
        score = 100 * len(pref_matched) / len(preferred)
    # A job naming one or two skills says little about fit: pull thin lists toward neutral.
    confidence = min(1.0, (len(required) + len(preferred) / 2) / 4)
    return round(min(score, 100) * confidence + 50 * (1 - confidence))


def _experience(f: JobFacts, user: UserFacts, r: MatchResult) -> int:
    if f.min_years is None:
        r.notes.append("Experience level not stated")
        return 60
    needed = _years(f.min_years, plus=True)
    if user.total_years is None:
        r.notes.append(f"{needed} required; add your total experience to your profile to compare")
        return 50
    if user.total_years >= f.min_years:
        r.reasons.append(f"{needed} required: you have {_years(user.total_years)}")
        return 100
    r.missing.append(f"{needed} of experience (you have {_years(user.total_years)})")
    return round(100 * user.total_years / f.min_years)


def _location(job: JobInput, user: UserFacts, r: MatchResult) -> int:
    workplace = job.facts.workplace
    location = (job.location or "").strip()
    pref = user.remote_preference
    if workplace is WorkplaceType.REMOTE:
        if pref in (RemotePreference.REMOTE, RemotePreference.ANY, RemotePreference.HYBRID):
            r.reasons.append(
                "Remote: matches your preference"
                if pref is RemotePreference.REMOTE
                else "Remote role"
            )
            return 100
        r.notes.append("Remote role; you prefer on-site")
        return 60

    places = [p for p in user.preferred_locations if norm(p) not in ("remote", "anywhere")]
    here = norm(location)
    in_preferred = bool(here) and any(
        norm(p) and (norm(p) in here or here in norm(p)) for p in places
    )
    score: int
    if in_preferred:
        r.reasons.append(f"In {location}: one of your preferred locations")
        score = 100
    elif not location:
        r.notes.append("Location not stated")
        score = 50
    elif not places:
        score = 70
    elif user.willing_to_relocate:
        r.notes.append(f"In {location}; you're open to relocating")
        score = 55
    else:
        r.concerns.append(f"In {location}: not one of your preferred locations")
        score = 20
    if pref is RemotePreference.REMOTE and workplace in (
        WorkplaceType.ONSITE,
        WorkplaceType.HYBRID,
    ):
        r.concerns.append(f"{workplace.value.capitalize()} role; you prefer remote")
        score = max(0, score - 30)
    return score


def _salary(f: JobFacts, user: UserFacts, r: MatchResult) -> int:
    if f.salary_min is None and f.salary_max is None:
        r.notes.append("Salary not listed")
        return 50
    currency = f.salary_currency or ""
    top = f.salary_max or f.salary_min or 0
    listed = (
        f"{_money(f.salary_min, currency)}–{_money(f.salary_max, currency)}"  # noqa: RUF001
        if f.salary_min and f.salary_max
        else _money(top, currency)
    )
    expectation, expectation_currency = _user_salary(user)
    if expectation is None:
        r.notes.append(f"Salary listed: {listed}")
        return 70
    if expectation_currency != currency:
        r.notes.append(
            f"Salary listed in {currency} ({listed}); your expectation is in {expectation_currency}"
        )
        return 50
    if top >= expectation:
        r.reasons.append(f"Pays up to {_money(top, currency)}: meets your expectation")
        return 100
    r.concerns.append(
        f"Pays up to {_money(top, currency)}, "
        f"below your {_money(expectation, currency)} expectation"
    )
    return round(100 * top / expectation)


def _user_salary(user: UserFacts) -> tuple[int | None, str | None]:
    if user.expected_salary_min is not None:
        return user.expected_salary_min, user.currency
    if user.min_salary is not None:
        return user.min_salary, user.salary_currency
    return None, None


def _preferences(job: JobInput, user: UserFacts, r: MatchResult) -> int:
    parts: list[tuple[float, float]] = []  # (score 0-1, weight)
    if user.preferred_titles and _tokens(job.title):
        best_title, best = max(
            ((t, title_similarity(t, job.title)) for t in user.preferred_titles),
            key=lambda item: item[1],
        )
        parts.append((best, 0.5))
        if best >= 0.6:
            r.reasons.append(f"Title matches your target “{best_title}”")
    if user.keywords:
        text = f"{job.title}\n{job.description}".casefold()
        hits = [k for k in user.keywords if k.casefold() in text]
        parts.append((len(hits) / len(user.keywords), 0.3))
        if hits:
            r.reasons.append(f"Mentions your keywords: {', '.join(hits[:4])}")
    if user.employment_types and job.facts.employment_type:
        ok = job.facts.employment_type in user.employment_types
        parts.append((1.0 if ok else 0.0, 0.2))
    if not parts:
        return 60
    return round(100 * sum(s * w for s, w in parts) / sum(w for _, w in parts))


def _other(f: JobFacts, user: UserFacts, r: MatchResult) -> int:
    if user.sponsorship_required:
        if f.sponsorship is False:
            r.concerns.append("Doesn't offer visa sponsorship, which you need")
            return 0
        if f.sponsorship is True:
            r.reasons.append("Offers visa sponsorship")
            return 100
        r.notes.append("Visa sponsorship not mentioned")
        return 50
    return 100


# ------------------------------------------------------------------ hard filters


def _exclusion(job: JobInput, user: UserFacts) -> str | None:
    company = norm(job.company)
    for excluded in user.excluded_companies:
        if norm(excluded) and (norm(excluded) == company or norm(excluded) in company):
            return f"{job.company} is on your excluded companies list"
    context = norm(f"{job.company} {job.department or ''} {job.title} {job.description[:600]}")
    for industry in user.excluded_industries:
        if norm(industry) and f" {norm(industry)} " in f" {context} ":
            return f"Mentions an industry you excluded: {industry}"
    f = job.facts
    if user.preferred_titles:
        # Obvious mismatch: nothing in common with any target role, and the title doesn't
        # name one of the user's skills either ("Python Developer" is kept).
        related = any(title_similarity(t, job.title) > 0 for t in user.preferred_titles)
        names_skill = any(
            norm(s) in user.skills for s in f.skill_evidence if f.skill_evidence[s] == job.title
        )
        if not related and not names_skill:
            return "Title doesn't match your target roles"
    if user.remote_only and f.workplace is not WorkplaceType.REMOTE:
        return "Not a remote role (you asked for remote only)"
    if user.min_salary is not None and f.salary_currency == user.salary_currency:
        top = f.salary_max or f.salary_min
        if top is not None and top < user.min_salary:
            return "Pays less than your minimum salary"
    if (
        user.employment_types
        and f.employment_type
        and f.employment_type not in user.employment_types
    ):
        kind = f.employment_type.value.replace("_", "-").capitalize()
        return f"{kind} isn't one of your employment types"
    if user.sponsorship_required and f.sponsorship is False:
        return "Doesn't offer the visa sponsorship you need"
    return None


# ------------------------------------------------------------------ resume choice


@dataclass(frozen=True)
class ResumeCandidate:
    id: str
    name: str
    is_default: bool
    skills: frozenset[str]  # normalized


def recommend_resume(facts: JobFacts, resumes: list[ResumeCandidate]) -> tuple[str, str] | None:
    """The resume covering most of the job's skills (default wins ties), with a reason."""
    if not resumes:
        return None
    wanted = [norm(s) for s in facts.required_skills + facts.preferred_skills]

    def coverage(resume: ResumeCandidate) -> tuple[int, bool]:
        return sum(1 for s in wanted if s in resume.skills), resume.is_default

    best = max(resumes, key=coverage)
    hits, _ = coverage(best)
    if wanted and hits:
        reason = f"Mentions {hits} of the {len(wanted)} skills this job asks for"
    else:
        reason = "Your default resume" if best.is_default else "Your most complete resume"
    return best.id, reason
