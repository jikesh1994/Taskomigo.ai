import { clsx } from "clsx";

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <svg
      className={clsx("animate-spin", className ?? "size-4")}
      viewBox="0 0 24 24"
      fill="none"
      role={label ? "status" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function FullPageSpinner() {
  return (
    <div className="flex flex-1 items-center justify-center py-24 text-muted">
      <Spinner className="size-6" label="Loading" />
    </div>
  );
}
