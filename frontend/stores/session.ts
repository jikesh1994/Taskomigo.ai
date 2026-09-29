// In-memory access-token store.
//
// The access token is never written to localStorage/sessionStorage, so an XSS payload
// can't lift a long-lived credential from storage. The refresh token lives only in an
// httpOnly cookie. After a reload, the session is restored by calling /auth/refresh.

import { TOKEN_REFRESH_MARGIN_MS } from "@/services/config";

export type SessionEndReason = "expired" | "signed_out";

let accessToken: string | null = null;
let expiresAt = 0;
const endListeners = new Set<(reason: SessionEndReason) => void>();

export function setAccessToken(token: string, expiresInSeconds: number): void {
  accessToken = token;
  expiresAt = Date.now() + expiresInSeconds * 1000;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function hasUsableAccessToken(now = Date.now()): boolean {
  return accessToken !== null && now < expiresAt - TOKEN_REFRESH_MARGIN_MS;
}

/** Forget the token and tell listeners (the auth provider) the session is over. */
export function endSession(reason: SessionEndReason): void {
  const hadSession = accessToken !== null;
  accessToken = null;
  expiresAt = 0;
  if (hadSession || reason === "signed_out") {
    endListeners.forEach((listener) => listener(reason));
  }
}

export function onSessionEnd(listener: (reason: SessionEndReason) => void): () => void {
  endListeners.add(listener);
  return () => endListeners.delete(listener);
}

/** Test helper. */
export function resetSessionForTests(): void {
  accessToken = null;
  expiresAt = 0;
  endListeners.clear();
}
