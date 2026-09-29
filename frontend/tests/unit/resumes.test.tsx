import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ResumeList } from "@/components/resumes/resume-list";
import { ResumeReview } from "@/components/resumes/resume-review";
import { ResumeUpload } from "@/components/resumes/resume-upload";
import { formatBytes, resumesApi, validateResumeFile } from "@/services/resumes";
import type { Resume, ResumeReview as Review, ReviewItem } from "@/types/api";
import { renderWithQuery } from "../helpers";

vi.mock("@/services/resumes", async (original) => {
  const actual = await original<typeof import("@/services/resumes")>();
  return {
    ...actual,
    resumesApi: {
      list: vi.fn(),
      get: vi.fn(),
      upload: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      reparse: vi.fn(),
      download: vi.fn(),
      review: vi.fn(),
      applyReview: vi.fn(),
    },
  };
});

const api = vi.mocked(resumesApi);

const conflict: ReviewItem = {
  id: "c1",
  kind: "conflict",
  field: "skill.years",
  label: "Python experience",
  question: "Profile and resume contain different experience values. Which should be used?",
  profile_value: "5 years",
  resume_value: "7 years",
  evidence: "Python - 7 years",
};
const additions: ReviewItem[] = [
  { ...conflict, id: "a1", kind: "addition", field: "skill.add", label: "Skill: Django", profile_value: null, resume_value: "Django (5 years)", evidence: "Django - 5 years" },
  { ...conflict, id: "a2", kind: "addition", field: "skill.add", label: "Skill: AWS", profile_value: null, resume_value: "AWS", evidence: "AWS" },
];
const review: Review = { resume_id: "r1", items: [conflict, ...additions] };

function resume(overrides: Partial<Resume> = {}): Resume {
  return {
    id: "r1",
    name: "Backend CV",
    original_filename: "backend.pdf",
    file_type: "pdf",
    size_bytes: 120_000,
    is_default: true,
    parse_status: "parsed",
    parse_error_code: null,
    parse_error: null,
    parser: "anthropic:claude-opus-5-5",
    parsed_at: "2026-09-29T00:00:00Z",
    created_at: "2026-09-29T00:00:00Z",
    pending_review: 3,
    ...overrides,
  };
}

beforeEach(() => {
  api.review.mockResolvedValue(review);
  api.applyReview.mockImplementation(async (_id, decisions) => ({
    applied: decisions.filter((d) => d.action === "use_resume" || d.action === "add").length,
    skipped: decisions.filter((d) => d.action === "keep_profile" || d.action === "skip").length,
    errors: [],
    review: { resume_id: "r1", items: review.items.filter((i) => !decisions.some((d) => d.id === i.id)) },
  }));
});

describe("validateResumeFile", () => {
  const file = (name: string, size = 10) => new File([new Uint8Array(size)], name);
  it("accepts PDF and DOCX within the limit", () => {
    expect(validateResumeFile(file("cv.pdf"))).toBeNull();
    expect(validateResumeFile(file("CV.DOCX"))).toBeNull();
  });
  it("explains what's wrong", () => {
    expect(validateResumeFile(file("cv.doc"))).toMatch(/\.docx or PDF/);
    expect(validateResumeFile(file("photo.png"))).toMatch(/PDF or Word/);
    expect(validateResumeFile(file("cv.pdf", 0))).toMatch(/empty/);
    expect(validateResumeFile(file("cv.pdf", 6 * 1024 * 1024))).toMatch(/5 MB/);
  });
  it("formats sizes", () => {
    expect(formatBytes(900)).toBe("900 B");
    expect(formatBytes(120_000)).toBe("117 KB");
    expect(formatBytes(2.5 * 1024 * 1024)).toBe("2.5 MB");
  });
});

describe("ResumeReview", () => {
  it("applies nothing until the user chooses, then sends exactly their choices", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ResumeReview resumeId="r1" />);

    const apply = await screen.findByRole("button", { name: "Choose options to apply" });
    expect(apply).toBeDisabled();
    expect(screen.getByText(conflict.question)).toBeInTheDocument();
    expect(screen.getAllByText(/From your resume/)[0]).toHaveTextContent("Python - 7 years");

    await user.click(screen.getByRole("radio", { name: /Use resume: 7 years/ }));
    await user.click(screen.getByRole("checkbox", { name: /Django/ }));
    await user.click(screen.getByRole("button", { name: "Apply 2 choices" }));

    await waitFor(() => expect(api.applyReview).toHaveBeenCalled());
    expect(api.applyReview).toHaveBeenCalledWith("r1", [
      { id: "c1", action: "use_resume" },
      { id: "a1", action: "add" },
    ]);
    expect(await screen.findByText("Done: 2 added to your profile.")).toBeInTheDocument();
  });

  it("can keep the profile value, select all additions, and dismiss the rest", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ResumeReview resumeId="r1" />);

    await user.click(await screen.findByRole("radio", { name: /Keep profile: 5 years/ }));
    await user.click(screen.getByRole("button", { name: "Select all" }));
    expect(screen.getByRole("checkbox", { name: /AWS/ })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Apply 3 choices" }));
    await waitFor(() =>
      expect(api.applyReview).toHaveBeenLastCalledWith("r1", [
        { id: "c1", action: "keep_profile" },
        { id: "a1", action: "add" },
        { id: "a2", action: "add" },
      ]),
    );
  });

  it("says when there is nothing to review", async () => {
    api.review.mockResolvedValueOnce({ resume_id: "r1", items: [] });
    renderWithQuery(<ResumeReview resumeId="r1" />);
    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });
});

describe("ResumeList", () => {
  it("shows parsing progress, results and review entry points", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ResumeList
        resumes={[resume(), resume({ id: "r2", name: "General", is_default: false, parse_status: "processing", pending_review: 0 })]}
      />,
    );
    const backend = screen.getByRole("article", { name: "Backend CV" });
    expect(within(backend).getByText("Default")).toBeInTheDocument();
    expect(within(backend).getByText(/3 items to review/)).toBeInTheDocument();
    const general = screen.getByRole("article", { name: "General" });
    expect(within(general).getByRole("status")).toHaveTextContent("Reading your resume");
    expect(within(general).getByRole("button", { name: "Make default" })).toBeInTheDocument();

    await user.click(within(backend).getByRole("button", { name: "Review 3" }));
    expect(await within(backend).findByText(conflict.question)).toBeInTheDocument();
  });

  it("explains failures and retries", async () => {
    const user = userEvent.setup();
    api.reparse.mockResolvedValue(resume({ parse_status: "pending" }));
    renderWithQuery(
      <ResumeList
        resumes={[
          resume({
            parse_status: "failed",
            parse_error_code: "ai_not_configured",
            parse_error: "AI features aren't set up yet, so this couldn't be processed.",
            pending_review: 0,
          }),
        ]}
      />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't read this resume");
    expect(alert).toHaveTextContent("AI features aren't set up yet");
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(api.reparse).toHaveBeenCalled());
    expect(api.reparse.mock.calls[0][0]).toBe("r1");
  });
});

describe("ResumeUpload", () => {
  it("rejects unsupported files before uploading", async () => {
    const user = userEvent.setup({ applyAccept: false });
    renderWithQuery(<ResumeUpload />);
    await user.upload(screen.getByLabelText("Upload a resume"), new File(["x"], "photo.png", { type: "image/png" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/PDF or Word/);
    expect(api.upload).not.toHaveBeenCalled();
  });

  it("uploads a valid resume and shows server errors", async () => {
    const user = userEvent.setup();
    api.upload.mockRejectedValueOnce(
      Object.assign(new Error("dup"), { name: "ApiError" }),
    );
    renderWithQuery(<ResumeUpload />);
    const file = new File(["%PDF-1.7"], "cv.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Upload a resume"), file);
    await waitFor(() => expect(api.upload).toHaveBeenCalledWith(file, undefined));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
