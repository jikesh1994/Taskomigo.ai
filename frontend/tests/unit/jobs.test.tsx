import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { JobCard } from "@/components/jobs/job-card";
import { JobDetailView } from "@/components/jobs/job-detail";
import { JobsBrowser } from "@/components/jobs/jobs-browser";
import { SourcesManager } from "@/components/jobs/sources-card";
import { ApiError } from "@/services/errors";
import { formatSalary, jobSourcesApi, jobsApi, timeAgo } from "@/services/jobs";
import type { JobDetail, JobList, JobSummary } from "@/types/api";
import { renderWithQuery } from "../helpers";

vi.mock("@/services/jobs", async (original) => {
  const actual = await original<typeof import("@/services/jobs")>();
  return {
    ...actual,
    jobsApi: {
      list: vi.fn(),
      get: vi.fn(),
      setStatus: vi.fn(),
      analyze: vi.fn(),
      search: vi.fn(),
      latestSearch: vi.fn(),
      rematch: vi.fn(),
      stats: vi.fn(),
    },
    jobSourcesApi: { list: vi.fn(), catalog: vi.fn(), add: vi.fn(), setEnabled: vi.fn(), remove: vi.fn() },
  };
});

const api = vi.mocked(jobsApi);
const sources = vi.mocked(jobSourcesApi);

function job(overrides: Partial<JobSummary> = {}): JobSummary {
  return {
    id: "j1",
    platform: "greenhouse",
    company: "Acme",
    title: "Senior Backend Engineer",
    location: "Remote - India",
    workplace: "remote",
    employment_type: "full_time",
    department: "Engineering",
    salary_min: 3_000_000,
    salary_max: 4_500_000,
    salary_currency: "INR",
    posted_at: new Date().toISOString(),
    first_seen_at: new Date().toISOString(),
    is_active: true,
    application_url: "https://boards.greenhouse.io/acme/jobs/101",
    overall_match: 82,
    scores: { skills: 88, experience: 100, location: 100, salary: 70, preferences: 100, other: 100 },
    reasons: ["Python required: on your profile (you have 6 years)", "Remote role"],
    missing_requirements: ["Kubernetes"],
    concerns: [],
    excluded_reason: null,
    below_min_score: false,
    status: "new",
    ...overrides,
  };
}

function detail(overrides: Partial<JobDetail> = {}): JobDetail {
  return {
    ...job(),
    description: "Build payments.\n• Strong Python skills",
    notes: ["Salary listed: ₹30 lakh–₹45 lakh"],
    facts: {
      required_skills: ["Python", "Kubernetes"],
      preferred_skills: ["Kafka"],
      skill_evidence: {},
      min_years: 5,
      years_evidence: "• 5+ years of experience building backend systems",
      workplace: "remote",
      workplace_evidence: null,
      salary_min: 3_000_000,
      salary_max: 4_500_000,
      salary_currency: "INR",
      salary_evidence: "Compensation: 30 - 45 LPA.",
      sponsorship: null,
      sponsorship_evidence: null,
      employment_type: "full_time",
    },
    weights: { skills: 40, experience: 20, location: 10, salary: 10, preferences: 10, other: 10 },
    min_match_score: 60,
    recommended_resume: { id: "r1", name: "Backend CV", reason: "Mentions 3 of the 5 skills this job asks for" },
    computed_at: "2026-09-29T00:00:00Z",
    closed_at: null,
    analysis_status: "none",
    analysis: null,
    analysis_error: null,
    analyzed_at: null,
    ...overrides,
  };
}

const list = (items: JobSummary[]): JobList => ({
  items,
  total: items.length,
  counts: { matches: items.length, saved: 1, skipped: 0, hidden: 2 },
  min_match_score: 60,
});

beforeEach(() => vi.resetAllMocks());

describe("helpers", () => {
  it("formats salaries", () => {
    expect(formatSalary(3_000_000, 4_500_000, "INR")).toBe("₹30L–₹45L");
    expect(formatSalary(170_400, 255_700, "USD")).toBe("$170,400–$255,700");
    expect(formatSalary(null, 90_000, "EUR")).toBe("€90,000");
    expect(formatSalary(null, null, null)).toBeNull();
  });

  it("describes ages", () => {
    const now = Date.parse("2026-09-29T12:00:00Z");
    expect(timeAgo("2026-09-29T01:00:00Z", now)).toBe("today");
    expect(timeAgo("2026-09-28T01:00:00Z", now)).toBe("yesterday");
    expect(timeAgo("2026-09-01T00:00:00Z", now)).toBe("4 weeks ago");
  });
});

describe("JobCard", () => {
  it("shows the score, reasons and what's missing, and saves", async () => {
    api.setStatus.mockResolvedValue(detail({ status: "saved" }));
    renderWithQuery(<JobCard job={job()} />);
    const card = screen.getByRole("article", { name: "Senior Backend Engineer at Acme" });
    expect(within(card).getByText("82")).toBeInTheDocument();
    expect(within(card).getByText(/Python required/)).toBeInTheDocument();
    expect(within(card).getByText("Missing: Kubernetes")).toBeInTheDocument();
    expect(within(card).getByText(/₹30L–₹45L/)).toBeInTheDocument();
    await userEvent.click(within(card).getByRole("button", { name: "Save" }));
    expect(api.setStatus).toHaveBeenCalledWith("j1", "saved");
  });

  it("explains why a job is hidden", () => {
    renderWithQuery(<JobCard job={job({ excluded_reason: "Not a remote role (you asked for remote only)" })} />);
    expect(screen.getByText("Hidden: Not a remote role (you asked for remote only)")).toBeInTheDocument();
  });
});

describe("JobsBrowser", () => {
  it("lists matches with a non-predictive disclaimer and switches tabs", async () => {
    api.list.mockResolvedValue(list([job()]));
    renderWithQuery(<JobsBrowser />);
    expect(await screen.findByText("Senior Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText(/aren.t a prediction of interviews or offers/)).toBeInTheDocument();
    expect(api.list).toHaveBeenLastCalledWith(expect.objectContaining({ tab: "matches", sort: "score" }));

    api.list.mockResolvedValue(list([]));
    await userEvent.click(screen.getByRole("tab", { name: /Saved/ }));
    await waitFor(() => expect(api.list).toHaveBeenLastCalledWith(expect.objectContaining({ tab: "saved" })));
    expect(await screen.findByText("Jobs you save appear here.")).toBeInTheDocument();
  });
});

describe("SourcesManager", () => {
  it("adds a board by link and shows server errors", async () => {
    sources.list.mockResolvedValue([]);
    sources.catalog.mockResolvedValue([{ platform: "greenhouse", board: "stripe", company: "Stripe", added: false }]);
    sources.add.mockRejectedValueOnce(
      new ApiError({ status: 422, code: "unsupported_source", message: "Paste a Greenhouse or Lever careers link." }),
    );
    renderWithQuery(<SourcesManager />);
    const input = await screen.findByLabelText("Add a company careers page");
    await userEvent.type(input, "https://linkedin.com/jobs/1");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(await screen.findByText("Paste a Greenhouse or Lever careers link.")).toBeInTheDocument();

    sources.add.mockResolvedValue({
      id: "s1", platform: "greenhouse", board: "stripe", company_name: "Stripe", enabled: true,
      last_synced_at: null, last_job_count: null, last_error: null,
    });
    await userEvent.click(screen.getByRole("button", { name: "Add Stripe" }));
    await waitFor(() => expect(sources.add.mock.lastCall?.[0]).toBe("greenhouse:stripe"));
  });
});

describe("JobDetailView", () => {
  it("shows the breakdown, evidence and suggested resume; apply is not available yet", async () => {
    api.get.mockResolvedValue(detail());
    renderWithQuery(<JobDetailView id="j1" />);
    expect(await screen.findByRole("heading", { name: "Senior Backend Engineer" })).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Skills" })).toHaveAttribute("aria-valuenow", "88");
    expect(screen.getByText("“5+ years of experience building backend systems”")).toBeInTheDocument();
    expect(screen.getByText("Backend CV")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Apply with AI/ })).toBeDisabled();
    expect(screen.getByText("Not stated", { selector: "span" })).toBeInTheDocument(); // sponsorship
  });

  it("runs the AI analysis and labels stated vs inferred points", async () => {
    api.get.mockResolvedValue(detail());
    api.analyze.mockResolvedValue(
      detail({
        analysis_status: "done",
        analysis: {
          summary: "A senior backend role.",
          seniority: { value: "senior", basis: "explicit", evidence: "Senior Backend Engineer" },
          requirements: [
            { text: "Python", category: "skill", importance: "required", basis: "explicit", evidence: "Strong Python skills" },
            { text: "CS degree", category: "education", importance: "required", basis: "inferred", evidence: "" },
          ],
          responsibilities: [],
          benefits: [],
          work_authorization: { value: "unknown", basis: "unknown", evidence: "" },
          downgraded: 1,
        },
      }),
    );
    renderWithQuery(<JobDetailView id="j1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Analyse with AI" }));
    expect(await screen.findByText("A senior backend role.")).toBeInTheDocument();
    const degree = screen.getByText("CS degree").closest("li")!;
    expect(within(degree).getByText("Inferred")).toBeInTheDocument();
    expect(within(screen.getByText("Python", { selector: "span" }).closest("li")!).getByText("Stated")).toBeInTheDocument();
  });

  it("shows a friendly message for a job that isn't yours", async () => {
    api.get.mockRejectedValue(new ApiError({ status: 404, code: "not_found", message: "Job not found." }));
    renderWithQuery(<JobDetailView id="nope" />);
    expect(await screen.findByText("Job not found")).toBeInTheDocument();
  });
});
