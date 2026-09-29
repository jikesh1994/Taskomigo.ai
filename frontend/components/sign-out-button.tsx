"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

/** RequireAuth redirects to /login once the session ends. */
export function SignOutButton() {
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);

  return (
    <Button
      variant="ghost"
      size="sm"
      loading={busy}
      onClick={async () => {
        setBusy(true);
        await logout().catch(() => undefined);
      }}
    >
      Sign out
    </Button>
  );
}
