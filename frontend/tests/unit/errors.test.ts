import { describe, expect, it } from "vitest";
import { ApiError, describeError, parseFieldErrors } from "@/services/errors";
import { errorResponse, jsonResponse } from "../helpers";

describe("parseFieldErrors", () => {
  it("maps request-body paths to form field names", () => {
    expect(
      parseFieldErrors([
        { field: "body.first_name", message: "String should have at least 1 character", type: "x" },
        { field: "body.preferred_titles.3", message: "too long" },
        { field: "body", message: "Value error, expected_salary_min must not exceed expected_salary_max" },
        { field: "max_applications_per_day", message: "must be at most 100" },
      ]),
    ).toEqual([
      { field: "first_name", message: "String should have at least 1 character" },
      { field: "preferred_titles", message: "Too long" },
      { field: null, message: "Expected_salary_min must not exceed expected_salary_max" },
      { field: "max_applications_per_day", message: "Must be at most 100" },
    ]);
  });

  it("ignores malformed details", () => {
    expect(parseFieldErrors(null)).toEqual([]);
    expect(parseFieldErrors([42, { field: "x" }, "oops"])).toEqual([]);
  });
});

describe("ApiError.fromResponse", () => {
  it("reads the backend error envelope", async () => {
    const error = await ApiError.fromResponse(
      errorResponse(422, "validation_error", "Request validation failed.", [
        { field: "body.email", message: "value is not a valid email address" },
      ]),
    );
    expect(error).toMatchObject({
      status: 422,
      code: "validation_error",
      message: "Request validation failed.",
      requestId: "req-1234567890",
      fieldErrors: [{ field: "email", message: "Value is not a valid email address" }],
    });
  });

  it("reads Retry-After on rate limiting", async () => {
    const response = jsonResponse(
      { error: { code: "rate_limited", message: "Too many requests.", details: null, request_id: null } },
      429,
      { "Retry-After": "42" },
    );
    const error = await ApiError.fromResponse(response);
    expect(error.retryAfterSeconds).toBe(42);
    expect(describeError(error)).toBe("Too many attempts. Please wait 42 seconds and try again.");
  });

  it("shows long waits (per-account login throttling) in minutes", () => {
    const error = new ApiError({ status: 429, code: "login_throttled", message: "x", retryAfterSeconds: 870 });
    expect(describeError(error)).toBe("Too many attempts. Please wait 15 minutes and try again.");
  });

  it("copes with non-JSON error bodies", async () => {
    const error = await ApiError.fromResponse(new Response("<html>Bad gateway</html>", { status: 502 }));
    expect(error).toMatchObject({ status: 502, code: "http_error" });
    expect(describeError(error)).toMatch(/something went wrong on our side/i);
  });
});

describe("describeError", () => {
  it("never leaks raw values for unknown errors", () => {
    expect(describeError(new Error("secret stack detail"))).toBe("Something went wrong. Please try again.");
  });

  it("includes a short reference for server errors", () => {
    const error = new ApiError({ status: 500, code: "internal_error", message: "x", requestId: "abcdef1234" });
    expect(describeError(error)).toContain("reference abcdef12");
  });
});
