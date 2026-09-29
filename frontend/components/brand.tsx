import { clsx } from "clsx";
import Link from "next/link";
import { LogoMark } from "@/components/logo-mark";
import { BRAND } from "@/lib/brand";

/** `compact` hides the wordmark on small screens (used in the crowded app header). */
export function Brand({ href = "/", compact = false }: { href?: string; compact?: boolean }) {
  return (
    <Link href={href} className="inline-flex shrink-0 items-center gap-2 font-semibold tracking-tight whitespace-nowrap">
      <LogoMark />
      <span className={clsx(compact && "sr-only sm:not-sr-only")}>{BRAND.name}</span>
    </Link>
  );
}
