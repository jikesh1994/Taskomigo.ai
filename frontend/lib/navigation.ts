import type { User } from "@/types/api";

/**
 * Accept only same-origin relative paths as a post-login redirect target, so `?next=`
 * can't be abused as an open redirect (`//evil.com`, `https://…`, `/\evil.com`).
 */
export function safeNextPath(value: string | null | undefined): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return null;
  }
  return value;
}

export function homeFor(user: User): string {
  return user.onboarding_completed_at ? "/dashboard" : "/onboarding";
}
