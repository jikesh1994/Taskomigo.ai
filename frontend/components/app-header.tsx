"use client";

import { clsx } from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brand } from "@/components/brand";
import { SignOutButton } from "@/components/sign-out-button";
import { useCurrentUser } from "@/hooks/use-auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/profile", label: "Profile" },
  { href: "/resumes", label: "Resumes" },
  { href: "/settings", label: "Settings" },
] as const;

export function AppHeader() {
  const pathname = usePathname();
  const user = useCurrentUser();

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:gap-6 lg:px-8">
        <Brand href="/dashboard" compact />
        <nav aria-label="Main" className="flex min-w-0 items-center gap-1 overflow-x-auto">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={clsx(
                  "shrink-0 rounded-lg px-3 py-1.5 text-sm whitespace-nowrap transition-colors",
                  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring",
                  active ? "bg-surface-2 font-medium text-fg" : "text-muted hover:text-fg",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <span className="hidden text-sm text-muted sm:inline" title={user.email}>
            {user.first_name} {user.last_name}
          </span>
          <SignOutButton />
        </div>
      </div>
    </header>
  );
}
