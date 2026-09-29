import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { ApiError, describeError } from "@/services/errors";

/**
 * Show an API error on a react-hook-form form.
 *
 * Field errors for fields in `fields` are attached to those inputs; `aliases` maps API
 * field names to form field names where they differ (e.g. start_date → start_month).
 * Anything else (model-level rules, conflicts, network or server errors) is returned
 * as one message to show at the top of the form, or null if every error found a field.
 */
export function applyApiError<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
  aliases: Partial<Record<string, Path<T>>> = {},
): string | null {
  if (!(error instanceof ApiError) || error.fieldErrors.length === 0) {
    return describeError(error);
  }
  const known = new Set<string>(fields);
  const unmatched: string[] = [];
  let focused = false;
  for (const { field, message } of error.fieldErrors) {
    const target = field === null ? null : (aliases[field] ?? field);
    if (target !== null && known.has(target)) {
      setError(target as Path<T>, { type: "server", message }, { shouldFocus: !focused });
      focused = true;
    } else {
      unmatched.push(message);
    }
  }
  if (unmatched.length > 0) return unmatched.join(" ");
  return focused ? null : describeError(error);
}
