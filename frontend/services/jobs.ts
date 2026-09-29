import type {
  CatalogEntry,
  JobDetail,
  JobList,
  JobListParams,
  JobMatchStatus,
  JobSource,
  JobStats,
  SearchRun,
  UUID,
} from "@/types/api";
import { request } from "@/services/http";

function query(params: JobListParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const jobSourcesApi = {
  list: () => request<JobSource[]>("/job-sources"),
  catalog: () => request<CatalogEntry[]>("/job-sources/catalog"),
  add: (source: string) => request<JobSource>("/job-sources", { method: "POST", body: { source } }),
  setEnabled: (id: UUID, enabled: boolean) =>
    request<JobSource>(`/job-sources/${id}`, { method: "PATCH", body: { enabled } }),
  remove: (id: UUID) => request<void>(`/job-sources/${id}`, { method: "DELETE" }),
};

export const jobsApi = {
  list: (params: JobListParams = {}) => request<JobList>(`/jobs${query(params)}`),
  get: (id: UUID) => request<JobDetail>(`/jobs/${id}`),
  setStatus: (id: UUID, status: JobMatchStatus) =>
    request<JobDetail>(`/jobs/${id}`, { method: "PATCH", body: { status } }),
  analyze: (id: UUID) => request<JobDetail>(`/jobs/${id}/analyze`, { method: "POST" }),
  search: () => request<SearchRun>("/jobs/search", { method: "POST" }),
  latestSearch: () => request<SearchRun | null>("/jobs/search/latest"),
  rematch: () => request<{ matched: number }>("/jobs/rematch", { method: "POST" }),
  stats: () => request<JobStats>("/jobs/stats"),
};

export const isSearchActive = (run: SearchRun | null | undefined) =>
  run?.status === "queued" || run?.status === "running";

const SYMBOLS: Record<string, string> = { USD: "$", EUR: "€", GBP: "£", INR: "₹" };

/** "₹30L–₹45L", "$170,400–$255,700" or null when the job lists no salary. */
export function formatSalary(min: number | null, max: number | null, currency: string | null): string | null {
  if (min === null && max === null) return null;
  const code = currency ?? "";
  const symbol = SYMBOLS[code] ?? (code ? `${code} ` : "");
  const one = (amount: number) =>
    code === "INR" && amount >= 100_000
      ? `${symbol}${Number((amount / 100_000).toFixed(1))}L`
      : `${symbol}${amount.toLocaleString("en-US")}`;
  if (min !== null && max !== null && min !== max) return `${one(min)}–${one(max)}`;
  return one((max ?? min)!);
}

export const WORKPLACE_LABELS: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "",
};

export const PLATFORM_LABELS: Record<string, string> = { greenhouse: "Greenhouse", lever: "Lever" };

/** "today", "3 days ago", "2 weeks ago". */
export function timeAgo(iso: string | null, now = Date.now()): string {
  if (!iso) return "";
  const days = Math.floor((now - new Date(iso).getTime()) / 86_400_000);
  if (Number.isNaN(days)) return "";
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}
