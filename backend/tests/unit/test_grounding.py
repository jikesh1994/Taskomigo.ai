"""The anti-fabrication guard: nothing the model says survives unless the resume says it."""

from __future__ import annotations

from app.ai.resume.grounding import ground
from tests.resume_fixtures import RESUME_TEXT, parsed_resume


def test_faithful_output_is_kept_intact() -> None:
    parsed = parsed_resume()
    result = ground(parsed, RESUME_TEXT)
    assert result.removed == []
    assert result.resume == parsed


def test_invented_skill_is_removed() -> None:
    parsed = parsed_resume(
        skills=[
            {"name": "Python", "years": 7, "evidence": "Python - 7 years"},
            {"name": "Kubernetes", "years": 4, "evidence": "Kubernetes - 4 years"},
        ]
    )
    result = ground(parsed, RESUME_TEXT)
    assert [s.name for s in result.resume.skills] == ["Python"]
    assert "skill 'Kubernetes'" in result.removed


def test_inflated_years_are_dropped_but_skill_kept() -> None:
    parsed = parsed_resume(skills=[{"name": "Python", "years": 10, "evidence": "Python - 7 years"}])
    skill = ground(parsed, RESUME_TEXT).resume.skills[0]
    assert skill.name == "Python" and skill.years is None


def test_invented_employer_and_degree_are_removed() -> None:
    parsed = parsed_resume(
        experiences=[
            {
                "title": "Staff Engineer",
                "company": "Google",
                "location": None,
                "start": "2019-01",
                "end": None,
                "is_current": True,
                "description": None,
                "technologies": [],
                "evidence": "Staff Engineer, Google",
            }
        ],
        education=[
            {
                "institution": "Stanford University",
                "degree": "PhD",
                "field_of_study": None,
                "start_year": None,
                "end_year": 2012,
                "grade": None,
                "evidence": "PhD, Stanford University",
            }
        ],
    )
    result = ground(parsed, RESUME_TEXT)
    assert result.resume.experiences == []
    assert result.resume.education == []


def test_invented_certification_total_years_and_links_are_removed() -> None:
    parsed = parsed_resume(
        certifications=[{"name": "CISSP", "issuer": "ISC2", "year": 2020, "evidence": "CISSP"}],
        total_years_experience=12,
        links=[{"kind": "portfolio", "url": "https://priya.dev"}],
        phone="+1 555 0100",
    )
    result = ground(parsed, RESUME_TEXT).resume
    assert result.certifications == []
    assert result.total_years_experience is None
    assert result.links == []
    assert result.phone is None


def test_invented_dates_and_technologies_are_stripped_from_real_roles() -> None:
    parsed = parsed_resume(
        experiences=[
            {
                "title": "Software Engineer",
                "company": "Initech",
                "location": None,
                "start": "2015-01",  # resume says 2018
                "end": "2021-05",
                "is_current": False,
                "description": None,
                "technologies": ["Python", "Rust"],
                "evidence": "Software Engineer, Initech",
            }
        ]
    )
    exp = ground(parsed, RESUME_TEXT).resume.experiences[0]
    assert exp.start is None
    assert exp.end == "2021-05"
    assert exp.technologies == ["Python"]


def test_matching_is_whole_word_and_case_insensitive() -> None:
    parsed = parsed_resume(
        skills=[
            {"name": "python", "years": None, "evidence": "Python - 7 years"},
            {"name": "Go", "years": None, "evidence": "Go"},  # only appears inside words
        ]
    )
    assert [s.name for s in ground(parsed, RESUME_TEXT).resume.skills] == ["python"]
