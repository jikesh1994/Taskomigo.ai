import { clsx } from "clsx";
import type { ReactNode } from "react";

interface SwitchProps {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
}

/** An accessible on/off switch (role="switch"). */
export function Switch({ id, checked, onChange, label, description, disabled }: SwitchProps) {
  return (
    <div className="flex items-start justify-between gap-6 py-3">
      <div className="text-sm">
        <label htmlFor={id} className={clsx("font-medium", disabled && "text-muted")}>
          {label}
        </label>
        {description && (
          <div id={`${id}-description`} className="mt-0.5 text-muted">
            {description}
          </div>
        )}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-describedby={description ? `${id}-description` : undefined}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={clsx(
          "relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors",
          "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring",
          "disabled:cursor-not-allowed disabled:opacity-50",
          checked ? "bg-primary" : "bg-line-strong",
        )}
      >
        <span
          aria-hidden
          className={clsx(
            "inline-block size-5 rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-5.5" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  );
}
