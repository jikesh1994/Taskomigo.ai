"use client";

import { clsx } from "clsx";
import { useState } from "react";
import { FormError } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useApplyReview, useResumeReview } from "@/hooks/use-resumes";
import { describeError } from "@/services/errors";
import type { ReviewAction, ReviewItem } from "@/types/api";

type Choice = ReviewAction | undefined;

/**
 * Differences between a parsed resume and the profile. Nothing changes until the user
 * picks an option and applies: conflicts need a side, additions need a tick.
 */
export function ResumeReview({ resumeId, onDone }: { resumeId: string; onDone?: () => void }) {
  const query = useResumeReview(resumeId);
  // Lives here, not in the form: the form remounts with fresh items after each apply.
  const [notice, setNotice] = useState<string | null>(null);
  return (
    <div className="space-y-4">
      {notice && <Alert tone="success">{notice}</Alert>}
      <QueryState query={query}>
        {(review) =>
          review.items.length === 0 ? (
            <Alert tone="success" title="All caught up">
              Your profile already matches this resume.
            </Alert>
          ) : (
            <ReviewForm
              key={review.items.map((i) => i.id).join()}
              resumeId={resumeId}
              items={review.items}
              onDone={onDone}
              onNotice={setNotice}
            />
          )
        }
      </QueryState>
    </div>
  );
}

interface ReviewFormProps {
  resumeId: string;
  items: ReviewItem[];
  onDone?: () => void;
  onNotice: (message: string | null) => void;
}

function ReviewForm({ resumeId, items, onDone, onNotice }: ReviewFormProps) {
  const apply = useApplyReview(resumeId);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [error, setError] = useState<string | null>(null);

  const conflicts = items.filter((i) => i.kind === "conflict");
  const additions = items.filter((i) => i.kind === "addition");
  const chosen = Object.entries(choices).filter((entry): entry is [string, ReviewAction] => Boolean(entry[1]));
  const set = (id: string, choice: Choice) => setChoices((current) => ({ ...current, [id]: choice }));

  const submit = async (decisions: [string, ReviewAction][]) => {
    setError(null);
    onNotice(null);
    try {
      const result = await apply.mutateAsync(decisions.map(([id, action]) => ({ id, action })));
      const parts = [
        result.applied && `${result.applied} added to your profile`,
        result.skipped && `${result.skipped} kept as is`,
      ].filter(Boolean);
      onNotice(parts.length ? `Done: ${parts.join(", ")}.` : null);
      if (result.errors.length) setError(result.errors.join(" "));
      else if (result.review.items.length === 0) onDone?.();
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <div className="space-y-6">
      <FormError message={error} />

      {conflicts.length > 0 && (
        <section aria-labelledby={`conflicts-${resumeId}`} className="space-y-3">
          <h3 id={`conflicts-${resumeId}`} className="text-sm font-semibold">
            Different values ({conflicts.length})
          </h3>
          <p className="text-sm text-muted">{conflicts[0].question}</p>
          <ul className="space-y-3">
            {conflicts.map((item) => (
              <li key={item.id} className="rounded-lg border border-line p-4">
                <fieldset>
                  <legend className="text-sm font-medium">{item.label}</legend>
                  <Evidence text={item.evidence} />
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <Option
                      name={item.id}
                      label="Keep profile"
                      value={item.profile_value ?? "—"}
                      checked={choices[item.id] === "keep_profile"}
                      onSelect={() => set(item.id, "keep_profile")}
                    />
                    <Option
                      name={item.id}
                      label="Use resume"
                      value={item.resume_value}
                      checked={choices[item.id] === "use_resume"}
                      onSelect={() => set(item.id, "use_resume")}
                    />
                  </div>
                </fieldset>
              </li>
            ))}
          </ul>
        </section>
      )}

      {additions.length > 0 && (
        <section aria-labelledby={`additions-${resumeId}`} className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 id={`additions-${resumeId}`} className="text-sm font-semibold">
              Found in your resume ({additions.length})
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setChoices((current) => ({
                  ...current,
                  ...Object.fromEntries(additions.map((i) => [i.id, "add" as const])),
                }))
              }
            >
              Select all
            </Button>
          </div>
          <p className="text-sm text-muted">Tick what you&apos;d like added to your profile.</p>
          <ul className="divide-y divide-line rounded-lg border border-line">
            {additions.map((item) => (
              <li key={item.id} className="flex items-start gap-3 p-4">
                <input
                  id={`add-${item.id}`}
                  type="checkbox"
                  className="mt-1 size-4 accent-primary"
                  checked={choices[item.id] === "add"}
                  onChange={(event) => set(item.id, event.target.checked ? "add" : undefined)}
                />
                <label htmlFor={`add-${item.id}`} className="min-w-0 flex-1 text-sm">
                  <span className="font-medium">{item.label.split(": ")[0]}:</span>{" "}
                  <span>{item.resume_value}</span>
                  <Evidence text={item.evidence} />
                </label>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-line pt-4">
        {additions.length > 0 && (
          <Button
            variant="ghost"
            onClick={() => submit(additions.filter((i) => choices[i.id] !== "add").map((i) => [i.id, "skip"]))}
            disabled={apply.isPending}
          >
            Dismiss unticked
          </Button>
        )}
        <Button onClick={() => submit(chosen)} disabled={chosen.length === 0} loading={apply.isPending}>
          {chosen.length ? `Apply ${chosen.length} ${chosen.length === 1 ? "choice" : "choices"}` : "Choose options to apply"}
        </Button>
      </div>
    </div>
  );
}

function Option(props: { name: string; label: string; value: string; checked: boolean; onSelect: () => void }) {
  return (
    <label
      className={clsx(
        "flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm transition-colors",
        props.checked ? "border-primary bg-primary-soft" : "border-line-strong hover:bg-surface-2",
      )}
    >
      <input
        type="radio"
        name={props.name}
        aria-label={`${props.label}: ${props.value}`}
        className="mt-0.5 accent-primary"
        checked={props.checked}
        onChange={props.onSelect}
      />
      <span>
        {/* The ": " keeps the accessible name readable ("Keep profile: 5 years"). */}
        <span className="block text-xs text-muted">
          {props.label}
          <span className="sr-only">: </span>
        </span>
        <span className="font-medium">{props.value}</span>
      </span>
    </label>
  );
}

function Evidence({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <span className="mt-1 block text-xs text-muted">
      From your resume: <q className="italic">{text}</q>
    </span>
  );
}
