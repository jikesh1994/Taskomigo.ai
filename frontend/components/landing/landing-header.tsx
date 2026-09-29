"use client";

import { Brand } from "@/components/brand";
import { LinkButton } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { BRAND } from "@/lib/brand";
import { homeFor } from "@/lib/navigation";

export function LandingHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas/55 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-[90rem] items-center gap-8 px-5 sm:px-8 lg:px-14">
        <Brand compact />
        <nav aria-label="Page sections" className="hidden items-center gap-7 text-sm text-muted md:flex">
          <a href="#how-it-works" className="transition-colors hover:text-fg">
            How it works
          </a>
          <a href="#pipeline" className="transition-colors hover:text-fg">
            The pipeline
          </a>
          <a href="#trust" className="transition-colors hover:text-fg">
            Why you can trust it
          </a>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <HeaderActions />
        </div>
      </div>
    </header>
  );
}

/** Signed-in visitors get a way back into the app instead of sign-up buttons. */
function HeaderActions() {
  const { status, user } = useAuth();
  if (status === "authenticated" && user) {
    return (
      <LinkButton href={homeFor(user)} size="sm" className="btn-glow">
        Open {BRAND.name}
      </LinkButton>
    );
  }
  return (
    <>
      <LinkButton href="/login" variant="ghost" size="sm">
        Sign in
      </LinkButton>
      <LinkButton href="/register" size="sm" className="btn-glow">
        Join early access
      </LinkButton>
    </>
  );
}
