// The browser talks to the API directly (not through a Next.js proxy) so the backend's
// per-client-IP rate limiting sees real client addresses. The frontend and API must be
// same-site (e.g. app.example.com + api.example.com, or localhost:3000 + localhost:8000)
// for the SameSite=Strict refresh cookie to be sent.
const CONFIGURED_API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);

/**
 * The API origin to call.
 *
 * In local development the page may be opened as localhost or 127.0.0.1. Those are
 * different sites to the browser, so calling the API on the *other* name would fail
 * CORS and drop the refresh cookie. When both the configured API and the page are on
 * loopback, use the page's hostname. Any non-loopback configuration is used as is.
 */
export function apiBaseUrl(
  configured: string = CONFIGURED_API_URL,
  pageHostname: string | undefined = typeof window === "undefined" ? undefined : window.location.hostname,
): string {
  if (!pageHostname) return configured;
  try {
    const url = new URL(configured);
    if (LOOPBACK_HOSTS.has(url.hostname) && LOOPBACK_HOSTS.has(pageHostname) && url.hostname !== pageHostname) {
      url.hostname = pageHostname;
      return url.toString().replace(/\/+$/, "");
    }
  } catch {
    // Not a valid absolute URL; use it unchanged.
  }
  return configured;
}

export const API_PREFIX = "/api/v1";

// Refresh this long before the access token actually expires, to absorb clock skew
// and request latency.
export const TOKEN_REFRESH_MARGIN_MS = 30_000;
