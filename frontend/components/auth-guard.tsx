"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { FullPageSpinner } from "@/components/ui/spinner";
import { useAuth } from "@/hooks/use-auth";
import { homeFor, safeNextPath } from "@/lib/navigation";

/** Renders children only for a signed-in user; otherwise sends them to /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status, endReason } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status !== "anonymous") return;
    // After an explicit sign-out, don't send the next person back to this page.
    if (endReason === "signed_out") {
      router.replace("/login");
      return;
    }
    router.replace(`/login?${new URLSearchParams({ next: pathname })}`);
  }, [status, endReason, pathname, router]);

  if (status !== "authenticated") return <FullPageSpinner />;
  return <>{children}</>;
}

/**
 * For /login and /register: a signed-in user goes straight to the app. This is also
 * the single place that redirects after a successful sign-in, honouring a safe `?next=`.
 */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { status, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status !== "authenticated" || !user) return;
    const next = safeNextPath(new URLSearchParams(window.location.search).get("next"));
    router.replace(next ?? homeFor(user));
  }, [status, user, router]);

  if (status !== "anonymous") return <FullPageSpinner />;
  return <>{children}</>;
}
