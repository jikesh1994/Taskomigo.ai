"""Deterministic facts from a job description. No AI: fast, free and explainable.

Every fact records the line it came from (`evidence`). Anything not found is `None`
("unknown"), never guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.jobs.skills_vocab import AMBIGUOUS, SKILLS
from app.jobs.types import WorkplaceType
from app.models.enums import EmploymentType

# Bump when extraction rules change: stored facts are recomputed on the next search.
EXTRACTOR_VERSION = 2

# ------------------------------------------------------------------ sections

_REQUIRED_HEADINGS = re.compile(
    r"^(?:minimum |basic |required |key )?(?:requirements?|qualifications|skills(?: required)?|"
    r"what you(?:'| wi)ll bring|what you bring|what we(?:'re| are) looking for|who you are|about you|"
    r"you (?:have|bring|should have)|must[- ]haves?|experience|your profile|you might be a fit if)\b",
    re.IGNORECASE,
)
_PREFERRED_HEADINGS = re.compile(
    r"^(?:preferred(?: qualifications| skills)?|nice[- ]to[- ]haves?|bonus(?: points)?|"
    r"good to have|pluses|desirable|extra credit|it(?:'s| is) a plus if|ideally)\b",
    re.IGNORECASE,
)
_OTHER_HEADINGS = re.compile(
    r"^(?:responsibilities|what you(?:'| wi)ll do|the role|about (?:the role|us|the team)|"
    r"who we are|benefits|perks|what we offer|compensation|our (?:mission|culture)|"
    r"equal opportunity|how we work|life at)\b",
    re.IGNORECASE,
)
_PREFERRED_LINE = re.compile(
    r"\b(?:preferred|a plus|nice to have|bonus|is an advantage|good to have)\b", re.I
)


def _heading_kind(line: str) -> str | None:
    if line.lstrip().startswith(("•", "-", "*", "–")):  # a bullet is content, not a heading
        return None
    stripped = line.strip(" :#").strip()
    if not stripped or len(stripped) > 70 or stripped.endswith("."):
        return None
    if _PREFERRED_HEADINGS.match(stripped):
        return "preferred"
    if _REQUIRED_HEADINGS.match(stripped):
        return "required"
    if _OTHER_HEADINGS.match(stripped):
        return "other"
    return None


# ------------------------------------------------------------------ skills


@lru_cache(maxsize=1)
def _vocab_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    return tuple(_skill_pattern(name, aliases) for name, aliases in SKILLS.items())


def _term(value: str) -> str:
    # Word boundaries that also work for C++, C#, .NET, Node.js, CI/CD.
    return rf"(?<![\w+#.]){re.escape(value)}(?![\w+#]|\.\w)"


def _skill_pattern(name: str, aliases: tuple[str, ...] = ()) -> tuple[str, re.Pattern[str]]:
    alias_part = "|".join(_term(a) for a in aliases)
    return name, re.compile("|".join(filter(None, [_term(name), alias_part])), re.IGNORECASE)


@lru_cache(maxsize=1)
def _ambiguous_patterns() -> dict[str, tuple[re.Pattern[str], re.Pattern[str] | None]]:
    """For words like "Go", "C", "R", "REST": the canonical spelling is case-sensitive and
    not followed by phrases like "go-to-market"; aliases ("golang") are always safe."""
    out: dict[str, tuple[re.Pattern[str], re.Pattern[str] | None]] = {}
    for name in AMBIGUOUS:
        bare = re.compile(_term(name) + r"(?!\s*-\s*to\b|\s+(?:to|live|beyond|above|ahead)\b)")
        aliases = SKILLS.get(name, ())
        alias = re.compile("|".join(_term(a) for a in aliases), re.IGNORECASE) if aliases else None
        out[name] = (bare, alias)
    return out


def find_skills(text: str, extra: tuple[str, ...] = ()) -> list[str]:
    """Canonical skill names mentioned in `text`, in first-mention order.

    Ambiguous words ("Go", "C", "R", …) count only via an alias, or when the same text
    also names another, unambiguous skill, which is how technology lists read
    ("Python, Go and PostgreSQL") and prose ("Go live next quarter") doesn't.
    """
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    ambiguous = _ambiguous_patterns()
    patterns = [p for p in _vocab_patterns() if p[0] not in ambiguous]
    patterns += [_skill_pattern(s) for s in extra if s and s not in ambiguous]
    for name, pattern in patterns:
        match = pattern.search(text)
        if match and name.casefold() not in seen:
            seen.add(name.casefold())
            found.append((match.start(), name))
    has_context = bool(found)
    wanted_ambiguous = set(ambiguous) | {s for s in extra if s in ambiguous}
    for name in wanted_ambiguous:
        bare, alias = ambiguous[name]
        match = (alias.search(text) if alias else None) or (
            bare.search(text) if has_context else None
        )
        if match and name.casefold() not in seen:
            seen.add(name.casefold())
            found.append((match.start(), name))
    return [name for _, name in sorted(found)]


# ------------------------------------------------------------------ years

_YEARS = re.compile(
    r"(?P<n>\d{1,2}(?:\.\d)?)\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b", re.I
)

# ------------------------------------------------------------------ salary

_CURRENCIES = {
    "$": "USD", "US$": "USD", "USD": "USD", "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP",
    "₹": "INR", "INR": "INR", "RS": "INR", "RS.": "INR", "CAD": "CAD", "C$": "CAD", "CA$": "CAD",
    "AUD": "AUD", "A$": "AUD", "SGD": "SGD", "S$": "SGD", "CHF": "CHF", "JPY": "JPY", "¥": "JPY",
}  # fmt: skip
_CUR = r"(?P<cur>US\$|CA\$|C\$|A\$|S\$|\$|€|£|₹|¥|Rs\.?|USD|EUR|GBP|INR|CAD|AUD|SGD|CHF|JPY)"
_AMOUNT = r"\d{1,3}(?:[,.\s]\d{3})+|\d+(?:\.\d+)?"
_SALARY = re.compile(
    rf"{_CUR}\s?(?P<lo>{_AMOUNT})\s?(?P<klo>[kK])?\s*(?:-|–|—|to)\s*(?:{_CUR.replace('cur', 'cur2')})?\s?"
    rf"(?P<hi>{_AMOUNT})\s?(?P<khi>[kK])?"
)
_LPA = re.compile(
    r"(?P<lo>\d{1,3}(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<hi>\d{1,3}(?:\.\d+)?)\s*(?:LPA|lakhs?|lacs?)\b",
    re.I,
)
_HOURLY = re.compile(r"^\s*(?:/|per)\s*(?:hr|hour)|^\s*hourly", re.I)


def _amount(value: str, thousands: str | None) -> int:
    digits = re.sub(r"[,\s]", "", value)
    if digits.count(".") == 1 and len(digits.split(".")[1]) == 3:  # European "120.000"
        digits = digits.replace(".", "")
    number = float(digits)
    return int(number * 1000) if thousands else int(number)


# ------------------------------------------------------------------ sponsorship

_NO_SPONSOR = re.compile(
    r"\b(?:not|unable to|cannot|can't|won't|will not|do not|does not|don't|doesn't|no)\s+"
    r"(?:\w+\s+){0,3}?sponsor|sponsorship (?:is )?(?:not|un)available|without (?:the need for )?"
    r"(?:(?:visa|employment|work)\s+)?sponsorship|not eligible for (?:visa )?sponsorship",
    re.I,
)
_SPONSOR = re.compile(
    r"\b(?:visa )?sponsorship (?:is )?(?:available|provided|offered|possible)|\bwe (?:can|will|do) sponsor\b",
    re.I,
)

# ------------------------------------------------------------------ workplace / type

_REMOTE = re.compile(
    r"\b(?:fully remote|remote[- ]first|100% remote|remote (?:role|position|job|work|friendly)|work from home|wfh)\b",
    re.I,
)
_HYBRID = re.compile(r"\bhybrid\b", re.I)
_ONSITE = re.compile(r"\b(?:on[- ]?site|in[- ]office|in the office \d|office[- ]based)\b", re.I)
_EMPLOYMENT = (
    (EmploymentType.INTERNSHIP, re.compile(r"\bintern(?:ship)?\b", re.I)),
    (
        EmploymentType.CONTRACT,
        re.compile(r"\bcontract(?:or)?\b(?! (?:negotiation|management))", re.I),
    ),
    (EmploymentType.PART_TIME, re.compile(r"\bpart[- ]time\b", re.I)),
    (EmploymentType.TEMPORARY, re.compile(r"\btemporary\b", re.I)),
    (EmploymentType.FULL_TIME, re.compile(r"\bfull[- ]time\b|\bpermanent\b", re.I)),
)


@dataclass
class JobFacts:
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    skill_evidence: dict[str, str] = field(default_factory=dict)
    min_years: float | None = None
    years_evidence: str | None = None
    workplace: WorkplaceType = WorkplaceType.UNKNOWN
    workplace_evidence: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_evidence: str | None = None
    sponsorship: bool | None = None  # True offered, False not offered, None unknown
    sponsorship_evidence: str | None = None
    employment_type: EmploymentType | None = None

    def to_dict(self) -> dict[str, object]:
        data = dict(self.__dict__)
        data["workplace"] = self.workplace.value
        data["employment_type"] = self.employment_type.value if self.employment_type else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobFacts:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        known["workplace"] = WorkplaceType(known.get("workplace") or WorkplaceType.UNKNOWN)
        employment = known.get("employment_type")
        known["employment_type"] = EmploymentType(employment) if employment else None
        return cls(**known)


def extract_facts(
    *,
    title: str,
    description: str,
    location: str | None = None,
    workplace: WorkplaceType = WorkplaceType.UNKNOWN,
    employment_type: EmploymentType | None = None,
    salary: tuple[int | None, int | None, str | None] = (None, None, None),
    extra_skills: tuple[str, ...] = (),
) -> JobFacts:
    """`workplace`, `employment_type` and `salary` are structured values from the platform,
    used in preference to anything found in the text."""
    facts = JobFacts(workplace=workplace, employment_type=employment_type)
    lines = [line.strip() for line in description.splitlines() if line.strip()]

    # Skills by section.
    section: str | None = None
    has_required_section = False
    by_kind: dict[str, list[str]] = {"required": [], "preferred": [], "other": []}
    line_kinds: list[str] = []
    for line in lines:
        kind = _heading_kind(line)
        if kind:
            section = kind
            has_required_section |= kind == "required"
            # No `continue`: a heading-like line can still name skills ("Experience with Go").
        line_kind = "preferred" if _PREFERRED_LINE.search(line) else (section or "other")
        line_kinds.append(line_kind)
        for skill in find_skills(line, extra_skills):
            facts.skill_evidence.setdefault(skill, line[:300])
            by_kind[line_kind].append(skill)
    for skill in find_skills(title, extra_skills):
        facts.skill_evidence.setdefault(skill, title)
        by_kind["required"].insert(0, skill)

    preferred = list(dict.fromkeys(by_kind["preferred"]))
    required = list(dict.fromkeys(by_kind["required"]))
    if not has_required_section:  # no structure: every mention counts as required
        required = list(dict.fromkeys(required + by_kind["other"]))
    facts.required_skills = required
    facts.preferred_skills = [s for s in preferred if s not in required]

    # Minimum years: "N+ years" on requirement lines (in a requirements section, or
    # mentioning experience). The highest one wins ("3+ years of Go" and "6+ years in
    # engineering" means 6); "a plus" lines count only when nothing else states years.
    candidates: list[tuple[bool, float, str]] = []
    for line, line_kind in zip(lines, line_kinds, strict=True):
        relevant = line_kind == "required" or "experience" in line.casefold()
        match = _YEARS.search(line) if relevant else None
        if match and float(match.group("n")) <= 30:
            candidates.append((line_kind == "preferred", float(match.group("n")), line))
    if candidates:
        # Required lines first, then the largest number of years.
        _, facts.min_years, evidence = sorted(candidates, key=lambda c: (c[0], -c[1]))[0]
        facts.years_evidence = evidence[:300]

    # Workplace, if the platform didn't say.
    if facts.workplace is WorkplaceType.UNKNOWN:
        loc = (location or "").casefold()
        if "remote" in loc:
            facts.workplace, facts.workplace_evidence = WorkplaceType.REMOTE, location
        elif "hybrid" in loc:
            facts.workplace, facts.workplace_evidence = WorkplaceType.HYBRID, location
        else:
            for pattern, value in (
                (_REMOTE, WorkplaceType.REMOTE),
                (_HYBRID, WorkplaceType.HYBRID),
                (_ONSITE, WorkplaceType.ONSITE),
            ):
                line = next((ln for ln in lines if pattern.search(ln)), None)
                if line:
                    facts.workplace, facts.workplace_evidence = value, line[:300]
                    break

    # Salary: structured first, then text.
    lo, hi, currency = salary
    if lo or hi:
        facts.salary_min, facts.salary_max, facts.salary_currency = lo, hi, currency
        facts.salary_evidence = "Salary listed by the employer"
    else:
        _salary_from_text(lines, facts)

    # Sponsorship.
    for line in lines:
        if _NO_SPONSOR.search(line):
            facts.sponsorship, facts.sponsorship_evidence = False, line[:300]
            break
        if _SPONSOR.search(line):
            facts.sponsorship, facts.sponsorship_evidence = True, line[:300]
            break

    if facts.employment_type is None:
        head = f"{title}\n" + "\n".join(lines[:15])
        facts.employment_type = next((t for t, p in _EMPLOYMENT if p.search(head)), None)
    return facts


def _salary_from_text(lines: list[str], facts: JobFacts) -> None:
    for line in lines:
        match = _SALARY.search(line)
        if match and not _HOURLY.match(line[match.end() :]):
            symbol = match.group("cur")
            currency = _CURRENCIES.get(symbol) or _CURRENCIES.get(symbol.upper().rstrip("."))
            low = _amount(match.group("lo"), match.group("klo") or match.group("khi"))
            high = _amount(match.group("hi"), match.group("khi"))
            if currency and 1000 <= low <= high:
                facts.salary_min, facts.salary_max, facts.salary_currency = low, high, currency
                facts.salary_evidence = line[:300]
                return
        lpa = _LPA.search(line)
        if lpa:
            low, high = float(lpa.group("lo")), float(lpa.group("hi"))
            if 0 < low <= high:
                facts.salary_min, facts.salary_max = int(low * 100_000), int(high * 100_000)
                facts.salary_currency, facts.salary_evidence = "INR", line[:300]
                return
