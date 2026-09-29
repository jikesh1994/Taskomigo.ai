import type { AuthResponse } from "@/types/api";
import { API_PREFIX, apiBaseUrl } from "@/services/config";
import { ApiError } from "@/services/errors";
import {
  endSession,
  getAccessToken,
  hasUsableAccessToken,
  setAccessToken,
} from "@/stores/session";

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: Method;
  body?: unknown;
  /** Attach the access token (default true). */
  auth?: boolean;
  /** Send cookies. Only the /auth endpoints need the refresh cookie. */
  withCredentials?: boolean;
  signal?: AbortSignal;
}

const REFRESH_LOCK = "job-agent:auth-refresh";

// ------------------------------------------------------------------ refresh
//
// Refresh tokens rotate on every use and the backend treats a second use of the same
// token as theft, revoking the whole session. Two concurrent refreshes would therefore
// sign the user out. We prevent that at two levels:
//   * within a tab, every caller shares one in-flight refresh promise;
//   * across tabs, refreshes are serialised with the Web Locks API, so the second tab
//     refreshes with the cookie the first tab just received.

let inflightRefresh: Promise<AuthResponse> | null = null;

export function refreshSession(): Promise<AuthResponse> {
  inflightRefresh ??= withCrossTabLock(performRefresh).finally(() => {
    inflightRefresh = null;
  });
  return inflightRefresh;
}

async function withCrossTabLock<T>(task: () => Promise<T>): Promise<T> {
  if (typeof navigator !== "undefined" && navigator.locks?.request) {
    return navigator.locks.request(REFRESH_LOCK, task);
  }
  return task();
}

async function performRefresh(): Promise<AuthResponse> {
  const response = await send("/auth/refresh", { method: "POST", withCredentials: true }, null);
  if (!response.ok) {
    const error = await ApiError.fromResponse(response);
    if (error.status === 401) endSession("expired");
    throw error;
  }
  const body = (await response.json()) as AuthResponse;
  setAccessToken(body.access_token, body.expires_in);
  return body;
}

async function ensureAccessToken(): Promise<string> {
  if (!hasUsableAccessToken()) await refreshSession();
  const token = getAccessToken();
  if (token === null) {
    throw new ApiError({ status: 401, code: "not_authenticated", message: "Please sign in." });
  }
  return token;
}

// ------------------------------------------------------------------ request

async function send(path: string, options: RequestOptions, token: string | null) {
  const headers: Record<string, string> = { Accept: "application/json" };
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;
  // FormData sets its own multipart Content-Type (with the boundary).
  if (options.body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(`${apiBaseUrl()}${API_PREFIX}${path}`, {
      method: options.method ?? "GET",
      headers,
      body:
        options.body === undefined ? undefined : isForm ? (options.body as FormData) : JSON.stringify(options.body),
      credentials: options.withCredentials ? "include" : "omit",
      cache: "no-store",
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw ApiError.network();
  }
}

/**
 * Send an API request and return the successful Response.
 *
 * Authenticated requests refresh the access token first when it is missing or about to
 * expire, and retry exactly once after a refresh if the API still answers 401.
 */
async function fetchOk(path: string, options: RequestOptions): Promise<Response> {
  const authenticated = options.auth ?? true;
  let response = await send(path, options, authenticated ? await ensureAccessToken() : null);

  if (authenticated && response.status === 401) {
    await refreshSession();
    response = await send(path, options, getAccessToken());
    if (response.status === 401) endSession("expired");
  }

  if (!response.ok) throw await ApiError.fromResponse(response);
  return response;
}

/** Call the API and return the parsed JSON body (undefined for 204). */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetchOk(path, options);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Download a file from the API (authenticated), e.g. an uploaded resume. */
export async function requestBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  return (await fetchOk(path, options)).blob();
}

/** Test helper. */
export function resetHttpForTests(): void {
  inflightRefresh = null;
}
