from __future__ import annotations

from dataclasses import dataclass

from app.ai.llm.base import LLMProvider
from app.ai.prompts import load_prompt
from app.ai.resume.extraction_schema import ResumeExtraction, to_parsed
from app.ai.resume.grounding import ground
from app.ai.resume.schema import ParsedResume
from app.core.logging import get_logger

logger = get_logger(__name__)

# v2: flat string schema (see extraction_schema.py). v1 is kept for reproducibility.
PROMPT = load_prompt("resume_parsing", 2)
# Keep requests bounded; a resume beyond this is almost certainly not a resume.
MAX_PROMPT_CHARS = 60_000


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    resume: ParsedResume
    removed: list[str]
    parser: str  # "<provider>:<model>"
    prompt_id: str


class ResumeParser:
    """Text → structured resume via the configured LLM, then grounded in the source."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def parse(self, text: str) -> ParseOutcome:
        extraction = await self.provider.generate_structured(
            system=PROMPT.system,
            prompt=PROMPT.render(resume_text=text[:MAX_PROMPT_CHARS]),
            output_model=ResumeExtraction,
        )
        result = ground(to_parsed(extraction), text)
        if result.removed:
            # Values only (no resume text) so logs stay free of personal data.
            logger.warning("resume_parse_ungrounded_values_removed", count=len(result.removed))
        return ParseOutcome(
            resume=result.resume,
            removed=result.removed,
            parser=f"{self.provider.name}:{self.provider.model}",
            prompt_id=PROMPT.id,
        )
