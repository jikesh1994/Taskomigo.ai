import { clsx } from "clsx";
import type { ComponentProps, ReactNode } from "react";

const controlBase =
  "block w-full rounded-lg border bg-surface px-3 text-sm text-fg shadow-xs " +
  "placeholder:text-muted/70 transition-colors " +
  "focus:outline-none focus:ring-4 focus:ring-ring focus:border-primary " +
  "disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-muted";

function controlClasses(invalid: boolean, className?: string) {
  return clsx(controlBase, invalid ? "border-danger" : "border-line-strong", className);
}

export const describedBy = (id: string, hasHint: boolean, hasError: boolean) =>
  [hasHint && `${id}-hint`, hasError && `${id}-error`].filter(Boolean).join(" ") || undefined;

interface FieldProps {
  id: string;
  label: ReactNode;
  error?: string;
  hint?: ReactNode;
  optional?: boolean;
  className?: string;
  children: ReactNode;
}

/** Label, control, hint and error message, wired together for screen readers. */
export function Field({ id, label, error, hint, optional, className, children }: FieldProps) {
  return (
    <div className={clsx("space-y-1.5", className)}>
      <label htmlFor={id} className="flex items-baseline justify-between text-sm font-medium">
        <span>{label}</span>
        {optional && <span className="text-xs font-normal text-muted">Optional</span>}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-xs text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

type Shared = Omit<FieldProps, "children"> & { controlClassName?: string };

export function TextField({
  id,
  label,
  error,
  hint,
  optional,
  className,
  controlClassName,
  ...props
}: Shared & Omit<ComponentProps<"input">, "id">) {
  return (
    <Field id={id} label={label} error={error} hint={hint} optional={optional} className={className}>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, Boolean(hint), Boolean(error))}
        className={controlClasses(Boolean(error), clsx("h-10", controlClassName))}
        {...props}
      />
    </Field>
  );
}

export function TextAreaField({
  id,
  label,
  error,
  hint,
  optional,
  className,
  controlClassName,
  ...props
}: Shared & Omit<ComponentProps<"textarea">, "id">) {
  return (
    <Field id={id} label={label} error={error} hint={hint} optional={optional} className={className}>
      <textarea
        id={id}
        rows={4}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, Boolean(hint), Boolean(error))}
        className={controlClasses(Boolean(error), clsx("py-2", controlClassName))}
        {...props}
      />
    </Field>
  );
}

export interface Option {
  value: string;
  label: string;
}

export function SelectField({
  id,
  label,
  error,
  hint,
  optional,
  className,
  controlClassName,
  options,
  ...props
}: Shared & Omit<ComponentProps<"select">, "id"> & { options: readonly Option[] }) {
  return (
    <Field id={id} label={label} error={error} hint={hint} optional={optional} className={className}>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, Boolean(hint), Boolean(error))}
        className={controlClasses(Boolean(error), clsx("h-10", controlClassName))}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

interface CheckboxProps extends Omit<ComponentProps<"input">, "type" | "id"> {
  id: string;
  label: ReactNode;
  description?: ReactNode;
}

export function Checkbox({ id, label, description, className, ...props }: CheckboxProps) {
  return (
    <div className={clsx("flex items-start gap-3", className)}>
      <input
        id={id}
        type="checkbox"
        aria-describedby={description ? `${id}-description` : undefined}
        className="mt-0.5 size-4 rounded border-line-strong accent-primary"
        {...props}
      />
      <div className="text-sm">
        <label htmlFor={id} className="font-medium">
          {label}
        </label>
        {description && (
          <p id={`${id}-description`} className="text-muted">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
