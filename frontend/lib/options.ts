import type { Option } from "@/components/ui/field";
import type { EmploymentType, RemotePreference, SkillProficiency } from "@/types/api";

export const REMOTE_PREFERENCE_OPTIONS: readonly { value: RemotePreference; label: string }[] = [
  { value: "any", label: "No preference" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];

export const EMPLOYMENT_TYPE_OPTIONS: readonly { value: EmploymentType; label: string }[] = [
  { value: "full_time", label: "Full-time" },
  { value: "part_time", label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "freelance", label: "Freelance" },
  { value: "temporary", label: "Temporary" },
  { value: "internship", label: "Internship" },
];

export const PROFICIENCY_OPTIONS: readonly { value: SkillProficiency; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
  { value: "expert", label: "Expert" },
];

export const TRI_STATE_OPTIONS: readonly Option[] = [
  { value: "", label: "Not specified" },
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

const CURRENCIES = [
  "INR", "USD", "EUR", "GBP", "CAD", "AUD", "SGD", "AED", "CHF", "JPY", "CNY", "HKD",
  "NZD", "SEK", "NOK", "DKK", "PLN", "BRL", "MXN", "ZAR",
];

/** Common ISO 4217 codes, plus `current` if the user already saved another one. */
export function currencyOptions(current?: string | null): Option[] {
  const codes = current && !CURRENCIES.includes(current) ? [current, ...CURRENCIES] : CURRENCIES;
  return [{ value: "", label: "Select…" }, ...codes.map((code) => ({ value: code, label: code }))];
}

export function labelFor<T extends string>(
  options: readonly { value: T; label: string }[],
  value: T | null | undefined,
): string | null {
  return options.find((option) => option.value === value)?.label ?? null;
}

// ICU (and so Chrome/Node) still reports some zones by their pre-rename IANA names.
// Show and store the current names; the backend accepts both.
const LEGACY_ZONE_NAMES: Record<string, string> = {
  "Asia/Calcutta": "Asia/Kolkata",
  "Asia/Katmandu": "Asia/Kathmandu",
  "Asia/Rangoon": "Asia/Yangon",
  "Asia/Saigon": "Asia/Ho_Chi_Minh",
  "Atlantic/Faeroe": "Atlantic/Faroe",
  "Europe/Kiev": "Europe/Kyiv",
  "Pacific/Enderbury": "Pacific/Kanton",
};

export const canonicalTimeZone = (zone: string): string => LEGACY_ZONE_NAMES[zone] ?? zone;

export function browserTimeZone(): string {
  try {
    return canonicalTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  } catch {
    return "UTC";
  }
}

/** IANA zones the browser knows (current names), always including UTC and `current`. */
export function timeZoneOptions(current?: string): Option[] {
  let zones: string[] = [];
  try {
    zones = Intl.supportedValuesOf("timeZone");
  } catch {
    zones = [];
  }
  const all = new Set(["UTC", ...zones.map(canonicalTimeZone)]);
  if (current) all.add(current);
  return [...all].sort().map((zone) => ({ value: zone, label: zone.replaceAll("_", " ") }));
}
