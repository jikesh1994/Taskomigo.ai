from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest, validate_password_strength
from app.schemas.preferences import PreferencesReplace, PreferencesUpdate
from app.schemas.profile import (
    ExperienceCreate,
    ExperienceUpdate,
    ProfileReplace,
    ProfileUpdate,
)
from app.schemas.user import UserUpdate


@pytest.mark.parametrize(
    ("password", "ok"),
    [
        ("short1", False),
        ("longenoughbutnodigits", False),
        ("1234567890123", False),
        (" padded-pass-123", False),
        ("correct-horse-42", True),
    ],
)
def test_password_policy(password: str, ok: bool) -> None:
    if ok:
        assert validate_password_strength(password) == password
    else:
        with pytest.raises(ValueError):
            validate_password_strength(password)


def test_register_normalizes_email_and_validates_timezone() -> None:
    req = RegisterRequest(
        email="  Ada@Example.COM ",
        password="x",
        first_name=" Ada ",
        last_name="L",
        timezone="Asia/Kolkata",
    )
    assert req.email == "ada@example.com"
    assert req.first_name == "Ada"
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="a@example.com", password="x", first_name="A", last_name="B", timezone="Mars/Base"
        )


def test_register_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="a@example.com",
            password="x",
            first_name="A",
            last_name="B",
            role="admin",  # type: ignore[call-arg]
        )


def test_experience_date_rules() -> None:
    ExperienceCreate(company="Acme", title="Dev", start_date=date(2020, 1, 1), is_current=True)
    with pytest.raises(ValidationError, match="current position"):
        ExperienceCreate(
            company="Acme",
            title="Dev",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
            is_current=True,
        )
    with pytest.raises(ValidationError, match="before start_date"):
        ExperienceCreate(
            company="Acme", title="Dev", start_date=date(2021, 1, 1), end_date=date(2020, 1, 1)
        )
    with pytest.raises(ValidationError, match="future"):
        ExperienceCreate(company="Acme", title="Dev", start_date=date.today() + timedelta(days=30))


def test_profile_salary_rules_and_list_normalization() -> None:
    profile = ProfileReplace(
        preferred_titles=["  Backend  Engineer", "backend engineer", "", "SRE"],
        expected_salary_min=10,
        expected_salary_max=20,
        currency="inr",
        github_url="https://github.com/ada",
    )
    assert profile.preferred_titles == ["Backend Engineer", "SRE"]
    assert profile.currency == "INR"
    assert profile.github_url == "https://github.com/ada"
    with pytest.raises(ValidationError, match="must not exceed"):
        ProfileReplace(expected_salary_min=20, expected_salary_max=10, currency="USD")
    with pytest.raises(ValidationError, match="currency is required"):
        ProfileReplace(expected_salary_min=20)
    with pytest.raises(ValidationError):
        ProfileReplace(github_url="javascript:alert(1)")


def test_patch_models_reject_null_for_required_columns() -> None:
    assert ProfileUpdate(headline=None).changes() == {"headline": None}
    with pytest.raises(ValidationError, match="cannot be null"):
        ProfileUpdate(remote_preference=None)
    with pytest.raises(ValidationError, match="cannot be null"):
        ExperienceUpdate(company=None)
    with pytest.raises(ValidationError, match="cannot be null"):
        PreferencesUpdate(auto_fill_enabled=None)
    assert UserUpdate(timezone="UTC").model_dump(exclude_unset=True) == {"timezone": "UTC"}


def test_preferences_auto_submit_requires_review_disabled() -> None:
    with pytest.raises(ValidationError, match="auto_submit_enabled"):
        PreferencesReplace(auto_submit_enabled=True)
    prefs = PreferencesReplace(auto_submit_enabled=True, review_before_submit=False)
    assert prefs.auto_submit_enabled
    with pytest.raises(ValidationError, match="salary_currency"):
        PreferencesReplace(min_salary=100)
