// Experience/education dates are stored as ISO dates (YYYY-MM-DD) but entered and shown
// by month, which is how people remember career history.

/** "2021-03-01" → "2021-03" for <input type="month">. */
export function toMonthInput(date: string | null | undefined): string {
  return date ? date.slice(0, 7) : "";
}

/** "2021-03" → "2021-03-01"; empty → null. */
export function fromMonthInput(month: string): string | null {
  return /^\d{4}-\d{2}$/.test(month) ? `${month}-01` : null;
}

export function currentMonth(now = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** "2021-03-01" → "Mar 2021". Parsed as UTC so the month never shifts by timezone. */
export function formatMonth(date: string | null | undefined): string {
  if (!date) return "";
  const parsed = new Date(`${date.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

export function formatRange(start: string | null, end: string | null, current = false): string {
  const from = formatMonth(start);
  const to = current ? "Present" : formatMonth(end);
  if (from && to) return `${from} – ${to}`;
  return from || to;
}
