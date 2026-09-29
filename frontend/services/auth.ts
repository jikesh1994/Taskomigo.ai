import type { AuthResponse, LoginPayload, RegisterPayload, User } from "@/types/api";
import { refreshSession, request } from "@/services/http";
import { endSession, setAccessToken } from "@/stores/session";

function startSession(response: AuthResponse): User {
  setAccessToken(response.access_token, response.expires_in);
  return response.user;
}

export async function login(payload: LoginPayload): Promise<User> {
  const response = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: payload,
    auth: false,
    withCredentials: true,
  });
  return startSession(response);
}

export async function register(payload: RegisterPayload): Promise<User> {
  const response = await request<AuthResponse>("/auth/register", {
    method: "POST",
    body: payload,
    auth: false,
    withCredentials: true,
  });
  return startSession(response);
}

/** Restore a session from the httpOnly refresh cookie (e.g. after a page reload). */
export async function restoreSession(): Promise<User> {
  return (await refreshSession()).user;
}

export async function logout(): Promise<void> {
  try {
    await request<void>("/auth/logout", { method: "POST", auth: false, withCredentials: true });
  } finally {
    // Sign out locally even if the server call failed; the cookie expires on its own.
    endSession("signed_out");
  }
}
