import type {
  Resume,
  ResumeDetail,
  ResumeReview,
  ResumeUpdate,
  ReviewAction,
  ReviewApplyResult,
  UUID,
} from "@/types/api";
import { request, requestBlob } from "@/services/http";

// Must match the backend's RESUME_MAX_BYTES and detection rules (it re-checks both).
export const RESUME_MAX_BYTES = 5 * 1024 * 1024;
export const RESUME_ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export const resumesApi = {
  list: () => request<Resume[]>("/resumes"),
  get: (id: UUID) => request<ResumeDetail>(`/resumes/${id}`),
  upload: (file: File, name?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (name?.trim()) form.append("name", name.trim());
    return request<Resume>("/resumes", { method: "POST", body: form });
  },
  update: (id: UUID, data: ResumeUpdate) => request<Resume>(`/resumes/${id}`, { method: "PATCH", body: data }),
  remove: (id: UUID) => request<void>(`/resumes/${id}`, { method: "DELETE" }),
  reparse: (id: UUID) => request<Resume>(`/resumes/${id}/parse`, { method: "POST" }),
  download: (id: UUID) => requestBlob(`/resumes/${id}/file`),
  review: (id: UUID) => request<ResumeReview>(`/resumes/${id}/review`),
  applyReview: (id: UUID, decisions: { id: string; action: ReviewAction }[]) =>
    request<ReviewApplyResult>(`/resumes/${id}/review`, { method: "POST", body: { decisions } }),
};

/** Client-side pre-check for instant feedback (the server validates the content too). */
export function validateResumeFile(file: File): string | null {
  const lower = file.name.toLowerCase();
  if (!lower.endsWith(".pdf") && !lower.endsWith(".docx")) {
    return lower.endsWith(".doc")
      ? "Old .doc files aren't supported. Please save it as .docx or PDF."
      : "Please choose a PDF or Word (.docx) file.";
  }
  if (file.size === 0) return "This file is empty.";
  if (file.size > RESUME_MAX_BYTES) return "Resumes can be at most 5 MB.";
  return null;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
