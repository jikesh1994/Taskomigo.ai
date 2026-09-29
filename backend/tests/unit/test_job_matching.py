from __future__ import annotations

from dataclasses import replace

from app.jobs.extract import extract_facts
from app.jobs.html_text import html_to_text
from app.jobs.matching import (
    DEFAULT_WEIGHTS,
    JobInput,
    ResumeCandidate,
    UserFacts,
    match_job,
    norm,
    normalize_weights,
    recommend_resume,
    title_similarity,
)
from app.models.enums import EmploymentType, RemotePreference
from tests.job_fixtures import BACKEND_JD


def _job(
    title: str = "Senior Backend Engineer", description: str = BACKEND_JD, **kw: object
) -> JobInput:
    text = html_to_text(description)
    location = kw.pop("location", "Remote - India")
    return JobInput(
        company=str(kw.pop("company", "Acme")),
        title=title,
        location=location,  # type: ignore[arg-type]
        department=None,
        description=text,
        facts=extract_facts(title=title, description=text, location=location),  # type: ignore[arg-type]
    )


def _user(**kw: object) -> UserFacts:
    base = UserFacts(
        skills={
            norm(s): (s, y) for s, y in (("Python", 6.0), ("PostgreSQL", None), ("Docker", None))
        },
        total_years=7,
        preferred_titles=("Backend Engineer",),
        preferred_locations=("Bengaluru",),
        remote_preference=RemotePreference.REMOTE,
    )
    return replace(base, **kw)  # type: ignore[arg-type]


def test_strong_match_explains_itself() -> None:
    result = match_job(_job(), _user())
    assert result.excluded_reason is None
    assert result.overall >= 70
    assert "Python required: on your profile (you have 6 years)" in result.reasons
    assert "5+ years required: you have 7 years" in result.reasons
    assert "Remote: matches your preference" in result.reasons
    assert "Kubernetes" in result.missing
    assert result.scores["experience"] == 100


def test_weights_change_overall_but_not_components() -> None:
    job, user = _job(), _user()
    default = match_job(job, user)
    skills_only = match_job(
        job,
        user,
        {"skills": 100, "experience": 0, "location": 0, "salary": 0, "preferences": 0, "other": 0},
    )
    assert skills_only.scores == default.scores
    assert skills_only.overall == default.scores["skills"]


def test_normalize_weights() -> None:
    assert normalize_weights(None) == DEFAULT_WEIGHTS
    assert normalize_weights({"skills": 10, "bogus": 99})["skills"] == 10
    assert normalize_weights(dict.fromkeys(DEFAULT_WEIGHTS, 0)) == DEFAULT_WEIGHTS


def test_missing_experience_is_proportional() -> None:
    result = match_job(_job(), _user(total_years=2.5))
    assert result.scores["experience"] == 50
    assert "5+ years of experience (you have 2.5 years)" in result.missing


def test_unknowns_are_neutral_notes_not_penalties() -> None:
    job = _job(description="<p>Join us as a Backend Engineer.</p>", location=None)
    result = match_job(job, _user(total_years=None))
    assert "Experience level not stated" in result.notes
    assert "Salary not listed" in result.notes
    assert result.scores["salary"] == 50


def test_hard_filters() -> None:
    assert match_job(_job(), _user(excluded_companies=("acme",))).excluded_reason
    onsite = _job(
        description="<p>Backend Engineer, on-site in our Pune office.</p>", location="Pune"
    )
    assert match_job(onsite, _user(remote_only=True)).excluded_reason == (
        "Not a remote role (you asked for remote only)"
    )
    low = match_job(_job(), _user(min_salary=6_000_000, salary_currency="INR"))
    assert low.excluded_reason == "Pays less than your minimum salary"
    contract = replace(_job(), facts=replace(_job().facts, employment_type=EmploymentType.CONTRACT))
    types = frozenset({EmploymentType.FULL_TIME})
    assert "Contract" in (match_job(contract, _user(employment_types=types)).excluded_reason or "")


def test_unrelated_title_is_excluded_but_skill_titles_are_kept() -> None:
    sales = _job(
        title="Account Executive", description="<p>Sell our product. 4+ years in sales.</p>"
    )
    assert match_job(sales, _user()).excluded_reason == "Title doesn't match your target roles"
    python_dev = _job(title="Python Developer", description="<p>Python services.</p>")
    assert match_job(python_dev, _user()).excluded_reason is None


def test_title_similarity_synonyms() -> None:
    assert title_similarity("Backend Engineer", "Senior Back-end Developer") == 1.0
    assert title_similarity("Software Engineer", "SDE II") == 0.5
    assert title_similarity("Data Scientist", "Account Executive") == 0.0


def test_salary_below_expectation_is_a_concern() -> None:
    result = match_job(_job(), _user(expected_salary_min=5_000_000, currency="INR"))
    assert result.scores["salary"] == 90
    assert any("below your ₹50 lakh expectation" in c for c in result.concerns)


def test_sponsorship() -> None:
    job = _job(description="<p>Backend Engineer. We cannot sponsor visas.</p>")
    result = match_job(job, _user(sponsorship_required=True))
    assert result.excluded_reason == "Doesn't offer the visa sponsorship you need"


def test_recommend_resume_prefers_coverage_then_default() -> None:
    facts = _job().facts
    resumes = [
        ResumeCandidate("a", "General", True, frozenset({"python"})),
        ResumeCandidate("b", "Backend", False, frozenset({"python", "postgresql", "docker"})),
    ]
    assert recommend_resume(facts, resumes)[0] == "b"  # type: ignore[index]
    empty = [
        ResumeCandidate("a", "General", True, frozenset()),
        ResumeCandidate("b", "B", False, frozenset()),
    ]
    assert recommend_resume(facts, empty) == ("a", "Your default resume")
    assert recommend_resume(facts, []) is None
