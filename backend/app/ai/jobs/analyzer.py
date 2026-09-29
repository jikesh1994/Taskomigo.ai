"""Job description → structured analysis, with every item marked explicit / inferred / unknown.

The model gets a flat schema (see app/ai/resume/extraction_schema.py for why). Its output
is then checked against the posting: an "explicit" item whose evidence can't be found in
the posting is downgraded to "inferred", and responsibilities/benefits that aren't in the
posting are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.ai.llm.base import LLMProvider
from app.ai.prompts import load_prompt
from app.ai.resume.grounding import _norm, _Source
from app.core.logging import get_logger

logger = get_logger(__name__)

PROMPT = load_prompt("job_analysis", 1)
MAX_PROMPT_CHARS = 40_000

Basis = Literal["explicit", "inferred"]
BasisOrUnknown = Literal["explicit", "inferred", "unknown"]
Seniority = Literal[
    "intern", "entry", "mid", "senior", "staff", "principal", "manager", "director",
    "executive", "unknown",
]  # fmt: skip
Category = Literal["skill", "experience", "education", "certification", "language", "other"]


class _Flat(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalyzedRequirement(_Flat):
    text: str
    category: Category
    importance: Literal["required", "preferred"]
    basis: Basis
    evidence: str


class JobAnalysisExtraction(_Flat):
    """What the model fills in (flat: strings, enums and lists only)."""

    summary: str
    seniority: Seniority
    seniority_basis: BasisOrUnknown
    seniority_evidence: str
    requirements: list[AnalyzedRequirement]
    responsibilities: list[str]
    benefits: list[str]
    work_authorization: str
    work_authorization_basis: BasisOrUnknown
    work_authorization_evidence: str


class AnalyzedFact(_Flat):
    value: str
    basis: BasisOrUnknown
    evidence: str


class JobAnalysis(_Flat):
    """Stored on the job and returned by the API."""

    summary: str
    seniority: AnalyzedFact
    requirements: list[AnalyzedRequirement]
    responsibilities: list[str]
    benefits: list[str]
    work_authorization: AnalyzedFact
    downgraded: int  # explicit items whose evidence wasn't found in the posting


@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    analysis: JobAnalysis
    analyzer: str
    prompt_id: str


def _mostly_in(text: str, source: _Source, ratio: float = 0.7) -> bool:
    words = [w for w in _norm(text).split() if len(w) > 2]
    return not words or sum(w in source.tokens for w in words) / len(words) >= ratio


def _grounded_phrases(values: list[str], source: _Source) -> list[str]:
    return list(dict.fromkeys(v.strip() for v in values if v.strip() and _mostly_in(v, source)))


def _fact(value: str, basis: str, evidence: str, source: _Source) -> tuple[AnalyzedFact, bool]:
    value = value.strip()
    if basis == "unknown" or not value or value.casefold() == "unknown":
        return AnalyzedFact(value="unknown", basis="unknown", evidence=""), False
    if basis != "explicit":
        return AnalyzedFact(value=value, basis="inferred", evidence=""), False
    if not source.supports(evidence):
        return AnalyzedFact(value=value, basis="inferred", evidence=""), True
    return AnalyzedFact(value=value, basis="explicit", evidence=evidence.strip()), False


def ground_analysis(extraction: JobAnalysisExtraction, posting: str) -> JobAnalysis:
    source = _Source(posting)
    downgraded = 0
    requirements: list[AnalyzedRequirement] = []
    seen: set[str] = set()
    for item in extraction.requirements:
        key = _norm(item.text)
        if not key or key in seen:
            continue
        seen.add(key)
        if item.basis == "explicit" and not source.supports(item.evidence):
            item = item.model_copy(update={"basis": "inferred", "evidence": ""})
            downgraded += 1
        elif item.basis == "inferred":
            item = item.model_copy(update={"evidence": ""})
        requirements.append(item)

    seniority, down1 = _fact(
        extraction.seniority, extraction.seniority_basis, extraction.seniority_evidence, source
    )
    authorization, down2 = _fact(
        extraction.work_authorization,
        extraction.work_authorization_basis,
        extraction.work_authorization_evidence,
        source,
    )
    return JobAnalysis(
        summary=extraction.summary.strip(),
        seniority=seniority,
        requirements=requirements,
        responsibilities=_grounded_phrases(extraction.responsibilities, source),
        benefits=_grounded_phrases(extraction.benefits, source),
        work_authorization=authorization,
        downgraded=downgraded + down1 + down2,
    )


class JobAnalyzer:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def analyze(
        self, *, title: str, company: str, location: str | None, description: str
    ) -> AnalysisOutcome:
        extraction = await self.provider.generate_structured(
            system=PROMPT.system,
            prompt=PROMPT.render(
                title=title,
                company=company,
                location=location or "Not stated",
                description=description[:MAX_PROMPT_CHARS],
            ),
            output_model=JobAnalysisExtraction,
            max_tokens=8000,
        )
        analysis = ground_analysis(extraction, f"{title}\n{location or ''}\n{description}")
        if analysis.downgraded:
            logger.info("job_analysis_evidence_downgraded", count=analysis.downgraded)
        return AnalysisOutcome(
            analysis=analysis,
            analyzer=f"{self.provider.name}:{self.provider.model}",
            prompt_id=PROMPT.id,
        )
