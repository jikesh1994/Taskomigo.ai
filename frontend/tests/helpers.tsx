import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import type { AuthResponse, Preferences, User } from "@/types/api";

export function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

export function errorResponse(status: number, code: string, message: string, details: unknown = null) {
  return jsonResponse({ error: { code, message, details, request_id: "req-1234567890" } }, status);
}

export const testUser: User = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "ada@example.com",
  first_name: "Ada",
  last_name: "Lovelace",
  phone: null,
  timezone: "UTC",
  role: "user",
  is_active: true,
  onboarding_completed_at: null,
  created_at: "2026-09-29T00:00:00Z",
};

export function authResponse(token = "access-1", expiresIn = 900): AuthResponse {
  return {
    access_token: token,
    refresh_token: "refresh-ignored-by-frontend",
    token_type: "bearer",
    expires_in: expiresIn,
    refresh_expires_at: "2026-10-13T00:00:00Z",
    user: testUser,
  };
}

export const testPreferences: Preferences = {
  id: "22222222-2222-2222-2222-222222222222",
  keywords: [],
  employment_types: [],
  excluded_companies: [],
  excluded_industries: [],
  min_salary: null,
  salary_currency: null,
  remote_only: false,
  min_match_score: 60,
  match_weights: {},
  max_applications_per_day: 20,
  max_concurrent_browser_sessions: 2,
  max_retries_per_application: 2,
  auto_fill_enabled: true,
  auto_answer_enabled: true,
  review_before_submit: true,
  auto_submit_enabled: false,
  updated_at: "2026-09-29T00:00:00Z",
};

export function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}
