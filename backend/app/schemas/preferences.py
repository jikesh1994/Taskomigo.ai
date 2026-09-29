from __future__ import annotations

import uuid
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.jobs.matching import COMPONENTS
from app.models.enums import EmploymentType
from app.schemas.common import CurrencyCode, ORMModel, PatchModel, StringList, UtcDatetime


def _check_weights(value: dict[str, int]) -> dict[str, int]:
    unknown = sorted(set(value) - set(COMPONENTS))
    if unknown:
        raise ValueError(f"Unknown weight(s): {', '.join(unknown)}. Use: {', '.join(COMPONENTS)}")
    if value and sum(value.values()) <= 0:
        raise ValueError("At least one weight must be above zero")
    return value


# Relative importance of each match component (0-100 each). `{}` means the defaults
# (skills 40, experience 20, location 10, salary 10, preferences 10, other 10).
MatchWeights = Annotated[
    dict[str, Annotated[int, Field(ge=0, le=100)]], AfterValidator(_check_weights)
]


class _PreferenceFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keywords: StringList = Field(default_factory=list)
    employment_types: list[EmploymentType] = Field(default_factory=list, max_length=6)
    excluded_companies: StringList = Field(default_factory=list)
    excluded_industries: StringList = Field(default_factory=list)
    min_salary: Annotated[int, Field(ge=0, le=1_000_000_000)] | None = None
    salary_currency: CurrencyCode | None = None
    remote_only: bool = False
    min_match_score: int = Field(default=60, ge=0, le=100)
    match_weights: MatchWeights = Field(default_factory=dict)
    max_applications_per_day: int = Field(default=20, ge=0)
    max_concurrent_browser_sessions: int = Field(default=2, ge=1)
    max_retries_per_application: int = Field(default=2, ge=0)
    auto_fill_enabled: bool = True
    auto_answer_enabled: bool = True
    review_before_submit: bool = True
    auto_submit_enabled: bool = False

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        check_preference_consistency(
            min_salary=self.min_salary,
            salary_currency=self.salary_currency,
            review_before_submit=self.review_before_submit,
            auto_submit_enabled=self.auto_submit_enabled,
        )
        return self


def check_preference_consistency(
    *,
    min_salary: int | None,
    salary_currency: str | None,
    review_before_submit: bool,
    auto_submit_enabled: bool,
) -> None:
    if min_salary is not None and salary_currency is None:
        raise ValueError("salary_currency is required when min_salary is set")
    if auto_submit_enabled and review_before_submit:
        raise ValueError(
            "auto_submit_enabled requires review_before_submit to be false "
            "(sensitive steps still always require approval)"
        )


class PreferencesReplace(_PreferenceFields):
    """PUT: full replacement; omitted fields reset to defaults."""


class PreferencesUpdate(PatchModel):
    """PATCH: only provided fields change. Consistency is re-checked after merging."""

    non_nullable_fields = frozenset(
        {
            "keywords",
            "employment_types",
            "excluded_companies",
            "excluded_industries",
            "remote_only",
            "min_match_score",
            "match_weights",
            "max_applications_per_day",
            "max_concurrent_browser_sessions",
            "max_retries_per_application",
            "auto_fill_enabled",
            "auto_answer_enabled",
            "review_before_submit",
            "auto_submit_enabled",
        }
    )

    keywords: StringList | None = None
    employment_types: list[EmploymentType] | None = Field(default=None, max_length=6)
    excluded_companies: StringList | None = None
    excluded_industries: StringList | None = None
    min_salary: Annotated[int, Field(ge=0, le=1_000_000_000)] | None = None
    salary_currency: CurrencyCode | None = None
    remote_only: bool | None = None
    min_match_score: int | None = Field(default=None, ge=0, le=100)
    match_weights: MatchWeights | None = None
    max_applications_per_day: int | None = Field(default=None, ge=0)
    max_concurrent_browser_sessions: int | None = Field(default=None, ge=1)
    max_retries_per_application: int | None = Field(default=None, ge=0)
    auto_fill_enabled: bool | None = None
    auto_answer_enabled: bool | None = None
    review_before_submit: bool | None = None
    auto_submit_enabled: bool | None = None


class PreferencesRead(ORMModel):
    id: uuid.UUID
    keywords: list[str]
    employment_types: list[EmploymentType]
    excluded_companies: list[str]
    excluded_industries: list[str]
    min_salary: int | None
    salary_currency: str | None
    remote_only: bool
    min_match_score: int
    match_weights: dict[str, int]
    max_applications_per_day: int
    max_concurrent_browser_sessions: int
    max_retries_per_application: int
    auto_fill_enabled: bool
    auto_answer_enabled: bool
    review_before_submit: bool
    auto_submit_enabled: bool
    updated_at: UtcDatetime
