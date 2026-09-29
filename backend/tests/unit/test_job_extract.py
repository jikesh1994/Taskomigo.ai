from __future__ import annotations

from app.jobs.extract import JobFacts, extract_facts, find_skills
from app.jobs.html_text import html_to_text
from app.jobs.skills_vocab import canonical_skill
from app.jobs.types import WorkplaceType
from app.models.enums import EmploymentType
from tests.job_fixtures import BACKEND_JD


def test_html_to_text_handles_escaped_greenhouse_content() -> None:
    escaped = "&lt;h3&gt;Requirements&lt;/h3&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;"
    lines = [line for line in html_to_text(escaped, escaped=True).splitlines() if line]
    assert lines == ["Requirements", "• Python"]


def test_html_to_text_drops_scripts_and_styles() -> None:
    assert html_to_text("<p>Hi</p><script>alert(1)</script><style>p{}</style>") == "Hi"


def test_sections_split_required_and_preferred_skills() -> None:
    facts = extract_facts(title="Senior Backend Engineer", description=html_to_text(BACKEND_JD))
    assert {"Python", "PostgreSQL", "Docker", "Kubernetes"} <= set(facts.required_skills)
    assert {"Kafka", "RabbitMQ"} <= set(facts.preferred_skills)
    assert not set(facts.required_skills) & set(facts.preferred_skills)
    assert facts.skill_evidence["Kafka"].startswith("• Kafka or RabbitMQ")
    assert facts.min_years == 5
    assert facts.years_evidence and "5+ years" in facts.years_evidence


def test_workplace_salary_and_unknowns() -> None:
    facts = extract_facts(
        title="Senior Backend Engineer",
        description=html_to_text(BACKEND_JD),
        location="Remote - India",
    )
    assert facts.workplace is WorkplaceType.REMOTE
    assert (facts.salary_min, facts.salary_max, facts.salary_currency) == (
        3_000_000,
        4_500_000,
        "INR",
    )
    assert facts.sponsorship is None and facts.sponsorship_evidence is None  # not stated


def test_structured_platform_values_win() -> None:
    facts = extract_facts(
        title="Engineer",
        description="Work from home. $100k - $150k",
        workplace=WorkplaceType.HYBRID,
        employment_type=EmploymentType.CONTRACT,
        salary=(90_000, 120_000, "USD"),
    )
    assert facts.workplace is WorkplaceType.HYBRID
    assert facts.employment_type is EmploymentType.CONTRACT
    assert (facts.salary_min, facts.salary_max) == (90_000, 120_000)


def test_usd_salary_text_and_hourly_ignored() -> None:
    usd = extract_facts(
        title="Engineer",
        description="The base salary range is $170,400 – $255,700.",  # noqa: RUF001 (en dash, as posted)
    )
    assert (usd.salary_min, usd.salary_max, usd.salary_currency) == (170_400, 255_700, "USD")
    hourly = extract_facts(title="Engineer", description="Pay: $40 - $60 per hour")
    assert hourly.salary_min is None


def test_sponsorship_statements() -> None:
    no = extract_facts(title="x", description="We are unable to sponsor visas for this role.")
    yes = extract_facts(title="x", description="Visa sponsorship is available.")
    assert no.sponsorship is False and yes.sponsorship is True


def test_ambiguous_skills_need_context() -> None:
    assert "Go" not in find_skills("Our go-to-market team will go above and beyond")
    assert "Go" in find_skills("Services in Go and Python")
    assert "Go" in find_skills("Experience with Golang")


def test_years_takes_the_highest_requirement() -> None:
    text = html_to_text(
        "<h3>Requirements</h3><ul><li>6+ years in engineering across many products</li>"
        "<li>3+ years of experience as a Golang engineer</li></ul>"
        "<h3>Preferred</h3><ul><li>10+ years of experience is a plus</li></ul>"
        "<h3>About us</h3><p>For 25 years we have served customers.</p>"
    )
    facts = extract_facts(title="Backend Engineer", description=text)
    assert facts.min_years == 6
    assert facts.years_evidence == "• 6+ years in engineering across many products"
    only_plus = extract_facts(title="x", description="5+ years of experience is a plus")
    assert only_plus.min_years == 5


def test_facts_round_trip() -> None:
    facts = extract_facts(title="Python Developer", description="Remote. 3+ years experience.")
    assert JobFacts.from_dict(facts.to_dict()) == facts


def test_canonical_skill_names() -> None:
    assert canonical_skill("postgres") == "PostgreSQL"
    assert canonical_skill("nodejs") == "Node.js"
    assert canonical_skill("  Obscure Tool ") == "Obscure Tool"
