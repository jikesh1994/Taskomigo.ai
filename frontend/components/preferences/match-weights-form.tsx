"use client";

import { useState, type FormEvent } from "react";
import { FormActions, FormError, useSavedFlag } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { useRematch } from "@/hooks/use-jobs";
import { usePreferences, useUpdatePreferences } from "@/hooks/use-preferences";
import { describeError } from "@/services/errors";
import type { MatchComponent, Preferences } from "@/types/api";

// Must match DEFAULT_WEIGHTS in backend/app/jobs/matching.py.
export const DEFAULT_WEIGHTS: Record<MatchComponent, number> = {
  skills: 40,
  experience: 20,
  location: 10,
  salary: 10,
  preferences: 10,
  other: 10,
};

const LABELS: Record<MatchComponent, { label: string; hint: string }> = {
  skills: { label: "Skills", hint: "Required and nice-to-have skills you have" },
  experience: { label: "Experience", hint: "Years of experience asked for" },
  location: { label: "Location", hint: "Remote, hybrid or your preferred cities" },
  salary: { label: "Salary", hint: "Advertised pay against your expectation" },
  preferences: { label: "Your preferences", hint: "Target titles, keywords and employment type" },
  other: { label: "Other requirements", hint: "Visa sponsorship, when you need it" },
};

const KEYS = Object.keys(DEFAULT_WEIGHTS) as MatchComponent[];

export function MatchWeightsForm() {
  const preferences = usePreferences();
  return <QueryState query={preferences}>{(p) => <Inner preferences={p} />}</QueryState>;
}

function Inner({ preferences }: { preferences: Preferences }) {
  const update = useUpdatePreferences();
  const rematch = useRematch();
  const [weights, setWeights] = useState<Record<MatchComponent, number>>({
    ...DEFAULT_WEIGHTS,
    ...preferences.match_weights,
  });
  const [error, setError] = useState<string | null>(null);
  const [saved, markSaved] = useSavedFlag();
  const total = KEYS.reduce((sum, key) => sum + weights[key], 0);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (total === 0) {
      setError("At least one part needs a weight above zero.");
      return;
    }
    try {
      const isDefault = KEYS.every((key) => weights[key] === DEFAULT_WEIGHTS[key]);
      await update.mutateAsync({ match_weights: isDefault ? {} : weights });
      await rematch.mutateAsync();
      markSaved();
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5">
      <FormError message={error} />
      <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
        {KEYS.map((key) => {
          const share = total ? Math.round((weights[key] / total) * 100) : 0;
          return (
            <div key={key}>
              <div className="flex items-baseline justify-between text-sm">
                <label htmlFor={`weight-${key}`} className="font-medium">
                  {LABELS[key].label}
                </label>
                <span className="text-muted tabular-nums">{share}%</span>
              </div>
              <input
                id={`weight-${key}`}
                type="range"
                min={0}
                max={100}
                step={5}
                value={weights[key]}
                aria-describedby={`weight-${key}-hint`}
                aria-valuetext={`${weights[key]} (${share}% of the score)`}
                onChange={(event) => setWeights({ ...weights, [key]: Number(event.target.value) })}
                className="mt-1 w-full accent-primary"
              />
              <p id={`weight-${key}-hint`} className="text-xs text-muted">
                {LABELS[key].hint}
              </p>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-muted">
        Saving re-scores your current jobs. Scores compare jobs with your own criteria; they don&apos;t predict
        hiring decisions.
      </p>
      <FormActions
        submitting={update.isPending || rematch.isPending}
        saved={saved}
        secondaryAction={
          <Button variant="ghost" onClick={() => setWeights({ ...DEFAULT_WEIGHTS })}>
            Reset to defaults
          </Button>
        }
      />
    </form>
  );
}
