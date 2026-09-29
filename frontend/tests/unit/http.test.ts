import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/services/errors";
import { refreshSession, request, requestBlob, resetHttpForTests } from "@/services/http";
import { getAccessToken, onSessionEnd, resetSessionForTests, setAccessToken } from "@/stores/session";
import { authResponse, errorResponse, jsonResponse } from "../helpers";

const fetchMock = vi.fn<typeof fetch>();

function calls(pathSuffix: string) {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith(pathSuffix));
}

function authHeader(call: Parameters<typeof fetch>) {
  return (call[1]?.headers as Record<string, string>).Authorization;
}

beforeEach(() => {
  resetSessionForTests();
  resetHttpForTests();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("refreshSession", () => {
  it("shares one in-flight refresh between concurrent callers", async () => {
    // Rotating refresh tokens: a second concurrent refresh would look like token theft.
    fetchMock.mockResolvedValue(jsonResponse(authResponse("fresh")));

    const results = await Promise.all([refreshSession(), refreshSession(), refreshSession()]);

    expect(calls("/auth/refresh")).toHaveLength(1);
    expect(results.every((r) => r.access_token === "fresh")).toBe(true);
    expect(getAccessToken()).toBe("fresh");
  });

  it("sends the refresh cookie and no body", async () => {
    fetchMock.mockResolvedValue(jsonResponse(authResponse()));
    await refreshSession();
    const [, init] = calls("/auth/refresh")[0];
    expect(init?.credentials).toBe("include");
    expect(init?.body).toBeUndefined();
  });

  it("serialises refreshes across tabs with the Web Locks API", async () => {
    const lockRequest = vi.fn((_name: string, task: () => Promise<unknown>) => task());
    vi.stubGlobal("navigator", { ...navigator, locks: { request: lockRequest } });
    fetchMock.mockResolvedValue(jsonResponse(authResponse()));

    await refreshSession();

    expect(lockRequest).toHaveBeenCalledWith("job-agent:auth-refresh", expect.any(Function));
  });

  it("starts a new refresh once the previous one settles", async () => {
    fetchMock.mockResolvedValue(jsonResponse(authResponse()));
    await refreshSession();
    fetchMock.mockResolvedValue(jsonResponse(authResponse()));
    await refreshSession();
    expect(calls("/auth/refresh")).toHaveLength(2);
  });
});

describe("request", () => {
  it("restores a missing access token before an authenticated call", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(authResponse("restored")))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));

    await expect(request("/profile")).resolves.toEqual({ ok: true });

    const [profileCall] = calls("/profile");
    expect(authHeader(profileCall)).toBe("Bearer restored");
    expect(profileCall[1]?.credentials).toBe("omit");
  });

  it("refreshes a token that is about to expire before using it", async () => {
    setAccessToken("stale", 10); // inside the 30s safety margin
    fetchMock
      .mockResolvedValueOnce(jsonResponse(authResponse("fresh")))
      .mockResolvedValueOnce(jsonResponse({}));

    await request("/profile");

    expect(authHeader(calls("/profile")[0])).toBe("Bearer fresh");
  });

  it("retries once after a 401 with a refreshed token", async () => {
    setAccessToken("revoked", 900);
    fetchMock
      .mockResolvedValueOnce(errorResponse(401, "token_expired", "Access token has expired."))
      .mockResolvedValueOnce(jsonResponse(authResponse("fresh")))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));

    await expect(request("/profile")).resolves.toEqual({ ok: true });

    const profileCalls = calls("/profile");
    expect(profileCalls.map(authHeader)).toEqual(["Bearer revoked", "Bearer fresh"]);
  });

  it("refreshes only once when several requests hit an expired token together", async () => {
    setAccessToken("stale", 1);
    fetchMock.mockImplementation(async (url) =>
      String(url).endsWith("/auth/refresh") ? jsonResponse(authResponse("fresh")) : jsonResponse({}),
    );

    await Promise.all([request("/profile"), request("/preferences"), request("/users/me")]);

    expect(calls("/auth/refresh")).toHaveLength(1);
  });

  it("ends the session when the refresh token is rejected", async () => {
    setAccessToken("revoked", 900);
    const ended = vi.fn();
    onSessionEnd(ended);
    fetchMock
      .mockResolvedValueOnce(errorResponse(401, "token_expired", "Access token has expired."))
      .mockResolvedValueOnce(errorResponse(401, "refresh_token_reused", "Please sign in again."));

    const error = await request("/profile").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("refresh_token_reused");
    expect(ended).toHaveBeenCalledWith("expired");
    expect(getAccessToken()).toBeNull();
  });

  it("does not send a token or retry for unauthenticated endpoints", async () => {
    fetchMock.mockResolvedValueOnce(errorResponse(401, "invalid_credentials", "Invalid email or password."));

    await expect(
      request("/auth/login", { method: "POST", body: {}, auth: false, withCredentials: true }),
    ).rejects.toMatchObject({ status: 401, code: "invalid_credentials" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(authHeader(fetchMock.mock.calls[0])).toBeUndefined();
  });

  it("sends FormData as multipart without forcing a JSON content type", async () => {
    setAccessToken("t", 900);
    fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }, 202));
    const form = new FormData();
    form.append("file", new File(["%PDF"], "cv.pdf"));

    await request("/resumes", { method: "POST", body: form });

    const [, init] = calls("/resumes")[0];
    expect(init?.body).toBe(form);
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    expect(authHeader(calls("/resumes")[0])).toBe("Bearer t");
  });

  it("downloads files as blobs with the same auth handling", async () => {
    setAccessToken("t", 900);
    fetchMock.mockResolvedValueOnce(new Response("%PDF-1.7", { status: 200 }));
    const blob = await requestBlob("/resumes/r1/file");
    expect(blob.size).toBe(8);
  });

  it("returns undefined for 204 responses", async () => {
    setAccessToken("t", 900);
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(request("/profile/skills/1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("reports network failures as a friendly ApiError", async () => {
    setAccessToken("t", 900);
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(request("/profile")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });
});
