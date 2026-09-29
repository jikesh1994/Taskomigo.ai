import { clsx } from "clsx";
import type { ReactNode } from "react";

type Tone = "done" | "active" | "paused";

const STEPS: { tone: Tone; text: ReactNode }[] = [
  { tone: "done", text: "Found 42 new roles for “Backend Engineer”" },
  { tone: "done", text: "9 match your profile. Skipped 3 companies you excluded" },
  {
    tone: "done",
    text: (
      <>
        Filled 11 of 12 fields for <strong className="font-medium text-fg">Senior Python Developer</strong>
      </>
    ),
  },
  { tone: "done", text: "Attached “Python Backend Resume”" },
];

function Dot({ tone }: { tone: Tone }) {
  return (
    <span
      aria-hidden
      className={clsx(
        "mt-1.5 size-2 shrink-0 rounded-full",
        tone === "done" && "bg-success",
        tone === "active" && "animate-pulse bg-primary",
        tone === "paused" && "bg-warning",
      )}
    />
  );
}

/** A static illustration of the agent at work, including a human-in-the-loop pause. */
export function AgentPreview() {
  return (
    <figure className="relative">
      <div
        aria-hidden
        className="absolute -inset-6 -z-10 rounded-[2rem] bg-[radial-gradient(60%_60%_at_50%_40%,var(--primary-soft),transparent)]"
      />
      <div className="glass overflow-hidden rounded-2xl">
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <span aria-hidden className="size-2 animate-pulse rounded-full bg-primary" />
            Your amigo is working
          </div>
          <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs text-muted">ABC Technologies</span>
        </div>
        <ul className="space-y-3 px-5 py-4 text-sm text-muted">
          {STEPS.map((step, i) => (
            <li key={i} className="flex gap-3">
              <Dot tone={step.tone} />
              <span>{step.text}</span>
            </li>
          ))}
        </ul>
        <div className="mx-5 mb-5 rounded-xl border border-warning/30 bg-warning-soft p-4">
          <div className="flex gap-3">
            <Dot tone="paused" />
            <div className="text-sm">
              <p className="font-medium">Paused. Your turn</p>
              <p className="mt-0.5 text-muted">
                This site needs you to create an account. Taskomigo never signs up on your behalf.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-lg border border-line-strong bg-surface px-3 py-1.5 text-xs font-medium">
                  Open browser
                </span>
                <span className="btn-glow rounded-lg px-3 py-1.5 text-xs font-medium text-white">
                  I’m done, continue
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-muted">Illustrative preview</figcaption>
    </figure>
  );
}
