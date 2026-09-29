"use client";

import { Button } from "@/components/ui/button";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="text-muted">An unexpected error occurred. Your saved data is safe.</p>
      <Button variant="secondary" onClick={reset}>
        Try again
      </Button>
    </main>
  );
}
