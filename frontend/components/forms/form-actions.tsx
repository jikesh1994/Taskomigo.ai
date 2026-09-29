"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/** What a host (onboarding step or settings page) can customise on a section form. */
export interface FormSlots {
  submitLabel?: string;
  /** Called after a successful save. */
  onSaved?: () => void;
  /** Extra buttons shown before the submit button, e.g. "Back". */
  secondaryAction?: ReactNode;
}

interface FormActionsProps {
  submitLabel?: string;
  submitting: boolean;
  secondaryAction?: ReactNode;
  saved?: boolean;
}

export function FormActions({
  submitLabel = "Save changes",
  submitting,
  secondaryAction,
  saved,
}: FormActionsProps) {
  return (
    <div className="flex flex-wrap items-center justify-end gap-3 border-t border-line pt-5">
      {saved && (
        <span role="status" className="mr-auto text-sm text-success">
          Saved
        </span>
      )}
      {secondaryAction}
      <Button type="submit" loading={submitting}>
        {submitLabel}
      </Button>
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return <Alert tone="danger">{message}</Alert>;
}

/** A "Saved" flag that clears itself after a few seconds. */
export function useSavedFlag(durationMs = 3000): [boolean, () => void] {
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), durationMs);
    return () => clearTimeout(timer);
  }, [saved, durationMs]);
  return [saved, () => setSaved(true)];
}
