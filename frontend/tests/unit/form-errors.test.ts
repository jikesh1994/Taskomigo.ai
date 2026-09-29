import { describe, expect, it, vi } from "vitest";
import { applyApiError } from "@/lib/form-errors";
import { ApiError } from "@/services/errors";

type Form = { start_month: string; title: string };

describe("applyApiError", () => {
  it("attaches field errors, honouring aliases, and focuses the first one", () => {
    const setError = vi.fn();
    const error = new ApiError({
      status: 422,
      code: "validation_error",
      message: "Request validation failed.",
      fieldErrors: [
        { field: "title", message: "Required" },
        { field: "start_date", message: "Invalid date" },
      ],
    });

    const message = applyApiError<Form>(error, setError, ["title", "start_month"], { start_date: "start_month" });

    expect(message).toBeNull();
    expect(setError).toHaveBeenNthCalledWith(1, "title", { type: "server", message: "Required" }, { shouldFocus: true });
    expect(setError).toHaveBeenNthCalledWith(
      2,
      "start_month",
      { type: "server", message: "Invalid date" },
      { shouldFocus: false },
    );
  });

  it("returns model-level and unknown-field messages for the form banner", () => {
    const setError = vi.fn();
    const error = new ApiError({
      status: 422,
      code: "validation_error",
      message: "Request validation failed.",
      fieldErrors: [{ field: null, message: "End date must not be before start date" }],
    });
    expect(applyApiError<Form>(error, setError, ["title"])).toBe("End date must not be before start date");
    expect(setError).not.toHaveBeenCalled();
  });

  it("describes errors without field details", () => {
    const error = new ApiError({ status: 409, code: "conflict", message: "Skill already exists." });
    expect(applyApiError<Form>(error, vi.fn(), ["title"])).toBe("Skill already exists.");
  });
});
