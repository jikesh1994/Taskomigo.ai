"use client";

import { useState, type FormEvent } from "react";
import { QueryState } from "@/components/query-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ConfirmButton } from "@/components/ui/confirm-button";
import { TextField } from "@/components/ui/field";
import {
  useAddSource,
  useJobSources,
  useRemoveSource,
  useSourceCatalog,
  useToggleSource,
} from "@/hooks/use-jobs";
import { describeError } from "@/services/errors";
import { PLATFORM_LABELS, timeAgo } from "@/services/jobs";
import type { JobSource } from "@/types/api";

/** The company job boards the user searches: add by link, pick suggestions, remove. */
export function SourcesManager() {
  const sources = useJobSources();
  return (
    <QueryState query={sources}>
      {(list) => (
        <div className="space-y-6">
          {list.length > 0 ? (
            <ul className="divide-y divide-line" aria-label="Your job boards">
              {list.map((source) => (
                <SourceRow key={source.id} source={source} />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">No job boards yet. Add one below or pick a suggestion.</p>
          )}
          <AddSourceForm />
          <Suggestions />
        </div>
      )}
    </QueryState>
  );
}

function SourceRow({ source }: { source: JobSource }) {
  const toggle = useToggleSource();
  const remove = useRemoveSource();
  const [error, setError] = useState<string | null>(null);
  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium">{source.company_name}</p>
          <p className="text-xs text-muted">
            {PLATFORM_LABELS[source.platform] ?? source.platform} · {source.board}
            {source.last_synced_at &&
              ` · ${source.last_job_count ?? 0} jobs, checked ${timeAgo(source.last_synced_at)}`}
          </p>
          {source.last_error && <p className="mt-1 text-xs text-warning">{source.last_error}</p>}
        </div>
        <Button
          variant="ghost"
          size="sm"
          aria-pressed={source.enabled}
          aria-label={`${source.enabled ? "Pause" : "Resume"} ${source.company_name}`}
          loading={toggle.isPending}
          onClick={() => run(() => toggle.mutateAsync({ id: source.id, enabled: !source.enabled }))}
        >
          {source.enabled ? "Pause" : "Resume"}
        </Button>
        <ConfirmButton
          label="Remove"
          confirmLabel="Remove"
          ariaLabel={`Remove ${source.company_name}`}
          onConfirm={() => run(() => remove.mutateAsync(source.id))}
        />
      </div>
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </li>
  );
}

function AddSourceForm() {
  const add = useAddSource();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!value.trim()) return;
    setError(null);
    try {
      await add.mutateAsync(value.trim());
      setValue("");
    } catch (err) {
      setError(describeError(err));
    }
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-wrap items-end gap-3">
      <TextField
        id="job-source"
        label="Add a company careers page"
        placeholder="https://boards.greenhouse.io/stripe"
        hint="Greenhouse and Lever job boards are supported."
        className="min-w-64 flex-1"
        value={value}
        error={error ?? undefined}
        onChange={(event) => setValue(event.target.value)}
      />
      <Button type="submit" variant="secondary" loading={add.isPending} className="mb-5">
        Add
      </Button>
    </form>
  );
}

function Suggestions() {
  const catalog = useSourceCatalog();
  const add = useAddSource();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const available = catalog.data?.filter((entry) => !entry.added) ?? [];
  if (available.length === 0) return null;

  const pick = async (key: string) => {
    setError(null);
    setPending(key);
    try {
      await add.mutateAsync(key);
      await catalog.refetch();
    } catch (err) {
      setError(describeError(err));
    } finally {
      setPending(null);
    }
  };

  return (
    <div>
      <p className="mb-2 text-sm font-medium">Suggested companies</p>
      <div className="flex flex-wrap gap-2">
        {available.map((entry) => {
          const key = `${entry.platform}:${entry.board}`;
          return (
            <Button
              key={key}
              variant="secondary"
              size="sm"
              loading={pending === key}
              disabled={pending !== null && pending !== key}
              aria-label={`Add ${entry.company}`}
              onClick={() => pick(key)}
            >
              + {entry.company}
            </Button>
          );
        })}
      </div>
      {error && (
        <Alert tone="danger" className="mt-3">
          {error}
        </Alert>
      )}
    </div>
  );
}
