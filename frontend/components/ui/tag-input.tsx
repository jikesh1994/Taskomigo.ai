"use client";

import { clsx } from "clsx";
import { useState, type KeyboardEvent } from "react";
import { Field, describedBy } from "@/components/ui/field";

interface TagInputProps {
  id: string;
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  max?: number;
  className?: string;
}

/** Free-text list entry: type and press Enter (or comma) to add; Backspace removes. */
export function TagInput({
  id,
  label,
  value,
  onChange,
  placeholder,
  hint,
  error,
  optional,
  max = 50,
  className,
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  const add = (raw: string) => {
    const item = raw.split(/\s+/).join(" ").trim();
    if (!item) return;
    const exists = value.some((v) => v.toLocaleLowerCase() === item.toLocaleLowerCase());
    if (!exists && value.length < max) onChange([...value, item.slice(0, 200)]);
    setDraft("");
  };

  const remove = (index: number) => onChange(value.filter((_, i) => i !== index));

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      add(draft);
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      remove(value.length - 1);
    }
  };

  return (
    <Field id={id} label={label} hint={hint} error={error} optional={optional} className={className}>
      <div
        className={clsx(
          "flex min-h-10 flex-wrap items-center gap-1.5 rounded-lg border bg-surface px-2 py-1.5",
          "focus-within:border-primary focus-within:ring-4 focus-within:ring-ring",
          error ? "border-danger" : "border-line-strong",
        )}
      >
        {value.length > 0 && (
        <ul className="contents" aria-label={`${label}: added`}>
          {value.map((item, index) => (
            <li
              key={item}
              className="inline-flex items-center gap-1 rounded-md bg-primary-soft py-0.5 pr-1 pl-2 text-sm"
            >
              {item}
              <button
                type="button"
                onClick={() => remove(index)}
                className="rounded px-1 text-muted hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`Remove ${item}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
        )}
        <input
          id={id}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => add(draft)}
          placeholder={value.length === 0 ? placeholder : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, Boolean(hint), Boolean(error))}
          className="h-7 min-w-32 flex-1 bg-transparent px-1 text-sm outline-none placeholder:text-muted/70"
        />
      </div>
    </Field>
  );
}
