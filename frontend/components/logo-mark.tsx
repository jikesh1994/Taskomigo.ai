import { clsx } from "clsx";

/** The Taskomigo mark: a friendly tick that doubles as a smile. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={clsx("shrink-0", className ?? "size-7")}>
      <rect width="32" height="32" rx="9" className="fill-primary" />
      <circle cx="11" cy="12" r="2" className="fill-on-primary" />
      <circle cx="21" cy="12" r="2" className="fill-on-primary" />
      <path
        d="M9.5 18.5l4.5 4.5 9-9"
        fill="none"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="stroke-on-primary"
      />
    </svg>
  );
}
