// Client-side validation that mirrors the backend rules (backend/app/schemas), so users
// get instant feedback. The API remains the source of truth and re-validates.
//
// Form controls hold strings; these schemas transform them into API payload values
// (empty string → null, numeric strings → numbers).

import { z } from "zod";

export const PASSWORD_MIN_LENGTH = 10;

export const passwordSchema = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Use at least ${PASSWORD_MIN_LENGTH} characters`)
  .max(128, "Use at most 128 characters")
  .refine((v) => v.trim() === v, "Don't start or end with a space")
  .refine((v) => /\p{L}/u.test(v) && /\d/.test(v), "Include at least one letter and one number");

export const emailSchema = z
  .string()
  .trim()
  .min(1, "Enter your email address")
  .pipe(z.email("Enter a valid email address"));

export const requiredText = (max: number, message: string) =>
  z.string().trim().min(1, message).max(max, `Keep it under ${max} characters`);

export const optionalText = (max: number) =>
  z
    .string()
    .trim()
    .max(max, `Keep it under ${max} characters`)
    .transform((v) => (v === "" ? null : v));

interface NumberRule {
  min: number;
  max: number;
  integer?: boolean;
}

export const optionalNumber = ({ min, max, integer = false }: NumberRule) =>
  z
    .string()
    .trim()
    .refine(
      (v) => v === "" || (Number.isFinite(Number(v)) && (!integer || Number.isInteger(Number(v)))),
      integer ? "Enter a whole number" : "Enter a number",
    )
    .refine((v) => v === "" || (Number(v) >= min && Number(v) <= max), `Enter a value from ${min} to ${max}`)
    .transform((v) => (v === "" ? null : Number(v)));

export const requiredInteger = ({ min, max }: Omit<NumberRule, "integer">) =>
  z
    .string()
    .trim()
    .min(1, "Required")
    .refine((v) => Number.isInteger(Number(v)), "Enter a whole number")
    .refine((v) => Number(v) >= min && Number(v) <= max, `Enter a value from ${min} to ${max}`)
    .transform(Number);

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return (url.protocol === "http:" || url.protocol === "https:") && url.hostname.includes(".");
  } catch {
    return false;
  }
}

export const optionalUrl = z
  .string()
  .trim()
  .max(500, "Keep it under 500 characters")
  .refine((v) => v === "" || isHttpUrl(v), "Enter a full link, starting with https://")
  .transform((v) => (v === "" ? null : v));

export const phoneSchema = z
  .string()
  .trim()
  .refine((v) => v === "" || /^\+?[0-9 ()-]{6,32}$/.test(v), "Use digits, spaces, ( ) or -, optionally starting with +")
  .transform((v) => (v === "" ? null : v));

/** Yes / No / "not specified" selects for nullable booleans. */
export type TriState = "" | "yes" | "no";
export const triStateSchema = z
  .enum(["", "yes", "no"])
  .transform((v) => (v === "" ? null : v === "yes"));
export const toTriState = (value: boolean | null): TriState =>
  value === null ? "" : value ? "yes" : "no";

export const numberToInput = (value: number | null | undefined): string =>
  value === null || value === undefined ? "" : String(value);
