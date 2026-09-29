import { describe, expect, it } from "vitest";
import { formatMonth, formatRange, fromMonthInput, toMonthInput } from "@/lib/dates";
import { homeFor, safeNextPath } from "@/lib/navigation";
import { canonicalTimeZone, timeZoneOptions } from "@/lib/options";
import {
  optionalNumber,
  optionalUrl,
  passwordSchema,
  phoneSchema,
  toTriState,
  triStateSchema,
} from "@/lib/validation";
import { testUser } from "../helpers";

describe("passwordSchema (mirrors the backend policy)", () => {
  it.each([
    ["short1", false],
    ["longenoughbutnodigits", false],
    ["1234567890123", false],
    [" leading-space-1", false],
    ["correct-horse-42", true],
    ["ünïcödé-pass-9", true],
  ])("%s → valid=%s", (password, valid) => {
    expect(passwordSchema.safeParse(password).success).toBe(valid);
  });
});

describe("optionalNumber", () => {
  const years = optionalNumber({ min: 0, max: 60 });
  const days = optionalNumber({ min: 0, max: 365, integer: true });

  it("turns empty input into null", () => {
    expect(years.parse("  ")).toBeNull();
  });
  it("parses numbers", () => {
    expect(years.parse("7.5")).toBe(7.5);
  });
  it("enforces bounds and integers", () => {
    expect(years.safeParse("61").success).toBe(false);
    expect(years.safeParse("abc").success).toBe(false);
    expect(days.safeParse("30.5").success).toBe(false);
    expect(days.parse("30")).toBe(30);
  });
});

describe("optionalUrl", () => {
  it("accepts http(s) URLs and rejects others", () => {
    expect(optionalUrl.parse("https://github.com/ada")).toBe("https://github.com/ada");
    expect(optionalUrl.parse("")).toBeNull();
    expect(optionalUrl.safeParse("github.com/ada").success).toBe(false);
    expect(optionalUrl.safeParse("javascript:alert(1)").success).toBe(false);
  });
});

describe("phoneSchema", () => {
  it("matches the backend pattern", () => {
    expect(phoneSchema.parse("+91 98765 43210")).toBe("+91 98765 43210");
    expect(phoneSchema.parse("")).toBeNull();
    expect(phoneSchema.safeParse("call me").success).toBe(false);
  });
});

describe("tri-state booleans", () => {
  it("round-trips null / true / false", () => {
    for (const value of [null, true, false]) {
      expect(triStateSchema.parse(toTriState(value))).toBe(value);
    }
  });
});

describe("safeNextPath", () => {
  it.each([
    ["/profile", "/profile"],
    ["/onboarding?step=skills", "/onboarding?step=skills"],
    ["//evil.example", null],
    ["/\\evil.example", null],
    ["https://evil.example", null],
    ["", null],
    [null, null],
  ])("%s → %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });

  it("sends new users to onboarding and finished users to the dashboard", () => {
    expect(homeFor(testUser)).toBe("/onboarding");
    expect(homeFor({ ...testUser, onboarding_completed_at: "2026-09-29T00:00:00Z" })).toBe("/dashboard");
  });
});

describe("time zones", () => {
  it("uses current IANA names instead of ICU's legacy ones", () => {
    expect(canonicalTimeZone("Asia/Calcutta")).toBe("Asia/Kolkata");
    expect(canonicalTimeZone("Europe/Berlin")).toBe("Europe/Berlin");
    const values = timeZoneOptions().map((o) => o.value);
    expect(values).toContain("UTC");
    expect(values).not.toContain("Asia/Calcutta");
  });

  it("keeps a saved zone even if the browser doesn't list it", () => {
    expect(timeZoneOptions("Etc/GMT+5").map((o) => o.value)).toContain("Etc/GMT+5");
  });
});

describe("month dates", () => {
  it("converts between ISO dates and month inputs", () => {
    expect(toMonthInput("2021-03-01")).toBe("2021-03");
    expect(toMonthInput(null)).toBe("");
    expect(fromMonthInput("2021-03")).toBe("2021-03-01");
    expect(fromMonthInput("")).toBeNull();
  });

  it("formats without shifting the month by timezone", () => {
    expect(formatMonth("2021-01-01")).toBe("Jan 2021");
    expect(formatRange("2020-01-01", null, true)).toBe("Jan 2020 – Present");
    expect(formatRange("2018-06-01", "2020-02-01")).toBe("Jun 2018 – Feb 2020");
  });
});
