from __future__ import annotations

import json

from app.ai.resume.extraction_schema import ResumeExtraction, XSkill, from_parsed, to_parsed
from app.ai.resume.parser import PROMPT
from tests.resume_fixtures import parsed_resume


def test_schema_has_no_nullable_fields() -> None:
    """Regression guard: nullable unions blew past Anthropic's structured-output grammar limit
    ("compiled grammar is too large"). The model-facing schema must stay flat."""
    schema = json.dumps(ResumeExtraction.model_json_schema())
    assert '"null"' not in schema
    assert "anyOf" not in schema


def test_roundtrip_preserves_the_parse() -> None:
    parsed = parsed_resume()
    assert to_parsed(from_parsed(parsed)) == parsed


def test_blank_strings_become_missing_values() -> None:
    extraction = from_parsed(parsed_resume()).model_copy(
        update={
            "phone": "  ",
            "total_years_experience": "",
            "skills": [
                XSkill(name="Python", years="7+", evidence="Python - 7+ years"),
                XSkill(name="Go", years="", evidence="Go"),
                XSkill(name=" ", years="3", evidence="?"),
            ],
        }
    )
    parsed = to_parsed(extraction)
    assert parsed.phone is None
    assert parsed.total_years_experience is None
    assert [(s.name, s.years) for s in parsed.skills] == [("Python", 7.0), ("Go", None)]


def test_current_role_has_no_end_date() -> None:
    extraction = from_parsed(parsed_resume())
    extraction.experiences[0].end = "2024-01"  # contradicts is_current
    assert to_parsed(extraction).experiences[0].end is None


def test_parser_uses_prompt_v2() -> None:
    assert PROMPT.id == "resume_parsing@v2"
    assert '""' in PROMPT.system  # the empty-string convention the schema relies on
