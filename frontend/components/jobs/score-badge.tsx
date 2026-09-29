import { clsx } from "clsx";

export function scoreTone(score: number): string {
  if (score >= 75) return "text-success border-success/40 bg-success-soft";
  if (score >= 55) return "text-primary border-primary/40 bg-primary-soft";
  return "text-warning border-warning/40 bg-warning-soft";
}

/** The overall match score. It describes fit with your criteria, not hiring odds. */
export function ScoreBadge({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  return (
    <span
      className={clsx(
        "grid shrink-0 place-items-center rounded-full border-2 font-semibold tabular-nums",
        size === "lg" ? "size-16 text-xl" : "size-12 text-base",
        scoreTone(score),
      )}
      title="Match score: how well this job fits your profile and preferences"
    >
      <span>
        {score}
        <span className="sr-only"> out of 100 match</span>
      </span>
    </span>
  );
}

export function ScoreBar({ label, score, weight }: { label: string; score: number; weight: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>
          {label}
          <span className="ml-1 text-xs text-muted">weight {weight}</span>
        </span>
        <span className="font-medium tabular-nums">{score}</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-surface-2"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
      >
        <div
          className={clsx(
            "h-full rounded-full",
            score >= 75 ? "bg-success" : score >= 55 ? "bg-primary" : "bg-warning",
          )}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
