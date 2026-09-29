import type { ErrorEnvelope } from "@/types/api";

export interface FieldError {
  /** Form field name, or null for errors about the request as a whole. */
  field: string | null;
  message: string;
}

/** An error returned by the API (or a network failure, with status 0). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldError[];
  readonly requestId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(init: {
    status: number;
    code: string;
    message: string;
    fieldErrors?: FieldError[];
    requestId?: string | null;
    retryAfterSeconds?: number | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.fieldErrors = init.fieldErrors ?? [];
    this.requestId = init.requestId ?? null;
    this.retryAfterSeconds = init.retryAfterSeconds ?? null;
  }

  static async fromResponse(response: Response): Promise<ApiError> {
    const retryAfter = Number(response.headers.get("Retry-After"));
    const base = {
      status: response.status,
      retryAfterSeconds: Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    };
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON error (e.g. a proxy's HTML page). Fall through to a generic error.
    }
    if (isErrorEnvelope(body)) {
      return new ApiError({
        ...base,
        code: body.error.code,
        message: body.error.message,
        fieldErrors: parseFieldErrors(body.error.details),
        requestId: body.error.request_id,
      });
    }
    return new ApiError({
      ...base,
      code: "http_error",
      message: `Request failed with status ${response.status}.`,
      requestId: response.headers.get("X-Request-ID"),
    });
  }

  static network(): ApiError {
    return new ApiError({
      status: 0,
      code: "network_error",
      message: "Can't reach the server. Check your connection and try again.",
    });
  }
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

/**
 * Normalises `details` into form-field errors.
 *
 * Request validation errors carry paths like `body.first_name` or
 * `body.preferred_titles.3`; the first segment after `body` is the form field.
 * A bare `body` path means a model-level rule (e.g. "min must not exceed max").
 * Service-level errors use plain names such as `password` or `max_applications_per_day`.
 */
export function parseFieldErrors(details: unknown): FieldError[] {
  if (!Array.isArray(details)) return [];
  return details.flatMap((item): FieldError[] => {
    if (typeof item !== "object" || item === null) return [];
    const { field, message } = item as { field?: unknown; message?: unknown };
    if (typeof message !== "string") return [];
    return [{ field: normaliseField(field), message: cleanMessage(message) }];
  });
}

function normaliseField(field: unknown): string | null {
  if (typeof field !== "string" || field === "") return null;
  const parts = field.split(".");
  if (parts[0] === "body") return parts[1] ?? null;
  return parts[0];
}

function cleanMessage(message: string): string {
  // Pydantic prefixes custom validator messages with "Value error, ".
  const stripped = message.replace(/^Value error,\s*/i, "");
  return stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

function formatWait(seconds: number): string {
  if (seconds < 90) return `${seconds} seconds`;
  const minutes = Math.ceil(seconds / 60);
  return `${minutes} minutes`;
}

/** A message suitable for showing to the user, for any thrown value. */
export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Something went wrong. Please try again.";
  }
  if (error.status === 429) {
    return error.retryAfterSeconds
      ? `Too many attempts. Please wait ${formatWait(error.retryAfterSeconds)} and try again.`
      : "Too many attempts. Please wait a moment and try again.";
  }
  if (error.status >= 500) {
    const reference = error.requestId ? ` (reference ${error.requestId.slice(0, 8)})` : "";
    return `Something went wrong on our side. Please try again${reference}.`;
  }
  return error.message;
}
