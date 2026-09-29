"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface ConfirmButtonProps {
  label: string;
  confirmLabel?: string;
  onConfirm: () => Promise<unknown> | void;
  /** Accessible name, e.g. "Delete Senior Engineer at Acme". */
  ariaLabel?: string;
}

/** A destructive action that asks for a second click instead of a browser dialog. */
export function ConfirmButton({ label, confirmLabel = "Confirm", onConfirm, ariaLabel }: ConfirmButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!confirming) {
    return (
      <Button variant="danger" size="sm" aria-label={ariaLabel} onClick={() => setConfirming(true)}>
        {label}
      </Button>
    );
  }
  return (
    <span className="inline-flex items-center gap-1">
      <Button
        variant="danger"
        size="sm"
        loading={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onConfirm();
          } finally {
            setBusy(false);
            setConfirming(false);
          }
        }}
      >
        {confirmLabel}
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setConfirming(false)} disabled={busy}>
        Cancel
      </Button>
    </span>
  );
}
