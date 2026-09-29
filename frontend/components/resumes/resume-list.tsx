"use client";

import { clsx } from "clsx";
import { useState } from "react";
import { FormError } from "@/components/forms/form-actions";
import { ResumeReview } from "@/components/resumes/resume-review";
import { Button } from "@/components/ui/button";
import { ConfirmButton } from "@/components/ui/confirm-button";
import { Spinner } from "@/components/ui/spinner";
import {
  useDeleteResume,
  useMakeDefaultResume,
  useRenameResume,
  useReparseResume,
} from "@/hooks/use-resumes";
import { describeError } from "@/services/errors";
import { formatBytes, resumesApi } from "@/services/resumes";
import type { Resume } from "@/types/api";

export function ResumeList({ resumes }: { resumes: Resume[] }) {
  const [reviewing, setReviewing] = useState<string | null>(null);
  if (resumes.length === 0) {
    return <p className="text-sm text-muted">No resumes yet. Upload one to get started.</p>;
  }
  return (
    <ul className="space-y-3" aria-label="Your resumes">
      {resumes.map((resume) => (
        <li key={resume.id}>
          <ResumeCard
            resume={resume}
            reviewing={reviewing === resume.id}
            onToggleReview={() => setReviewing((current) => (current === resume.id ? null : resume.id))}
          />
        </li>
      ))}
    </ul>
  );
}

function ResumeCard({
  resume,
  reviewing,
  onToggleReview,
}: {
  resume: Resume;
  reviewing: boolean;
  onToggleReview: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const makeDefault = useMakeDefaultResume();
  const reparse = useReparseResume();
  const remove = useDeleteResume();

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(describeError(err));
    }
  };

  const download = () =>
    run(async () => {
      const blob = await resumesApi.download(resume.id);
      const url = URL.createObjectURL(blob);
      const link = Object.assign(document.createElement("a"), { href: url, download: resume.original_filename });
      link.click();
      URL.revokeObjectURL(url);
    });

  return (
    <article
      aria-label={resume.name}
      className={clsx("rounded-xl border bg-surface", resume.is_default ? "border-primary/50" : "border-line")}
    >
      <div className="flex flex-wrap items-start gap-4 p-4">
        <span
          aria-hidden
          className={clsx(
            "grid size-10 shrink-0 place-items-center rounded-lg text-[11px] font-bold uppercase",
            resume.file_type === "pdf" ? "bg-danger-soft text-danger" : "bg-primary-soft text-primary",
          )}
        >
          {resume.file_type}
        </span>
        <div className="min-w-0 flex-1">
          {renaming ? (
            <RenameForm resume={resume} onDone={() => setRenaming(false)} />
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-medium">{resume.name}</h3>
              {resume.is_default && (
                <span className="rounded-full bg-primary-soft px-2 py-0.5 text-xs font-medium text-primary">
                  Default
                </span>
              )}
            </div>
          )}
          <p className="mt-0.5 truncate text-xs text-muted">
            {resume.original_filename} · {formatBytes(resume.size_bytes)} · uploaded{" "}
            {new Date(resume.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
          </p>
          <Status resume={resume} onRetry={() => run(() => reparse.mutateAsync(resume.id))} retrying={reparse.isPending} />
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {resume.parse_status === "parsed" && resume.pending_review > 0 && (
            <Button size="sm" onClick={onToggleReview} aria-expanded={reviewing}>
              {reviewing ? "Hide review" : `Review ${resume.pending_review}`}
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={download}>
            Download
          </Button>
          {!resume.is_default && (
            <Button
              variant="ghost"
              size="sm"
              loading={makeDefault.isPending}
              onClick={() => run(() => makeDefault.mutateAsync(resume.id))}
            >
              Make default
            </Button>
          )}
          {!renaming && (
            <Button variant="ghost" size="sm" onClick={() => setRenaming(true)}>
              Rename
            </Button>
          )}
          <ConfirmButton
            label="Delete"
            ariaLabel={`Delete ${resume.name}`}
            onConfirm={() => run(() => remove.mutateAsync(resume.id))}
          />
        </div>
      </div>
      {error && (
        <div className="px-4 pb-4">
          <FormError message={error} />
        </div>
      )}
      {reviewing && (
        <div className="border-t border-line p-4">
          <ResumeReview resumeId={resume.id} onDone={onToggleReview} />
        </div>
      )}
    </article>
  );
}

function Status({ resume, onRetry, retrying }: { resume: Resume; onRetry: () => void; retrying: boolean }) {
  switch (resume.parse_status) {
    case "pending":
    case "processing":
      return (
        <p role="status" className="mt-2 flex items-center gap-2 text-sm text-muted">
          <Spinner className="size-3.5" /> Reading your resume…
        </p>
      );
    case "parsed":
      return (
        <p className="mt-2 text-sm text-success">
          ✓ Read successfully
          {resume.pending_review > 0
            ? ` · ${resume.pending_review} ${resume.pending_review === 1 ? "item" : "items"} to review`
            : " · matches your profile"}
        </p>
      );
    case "failed":
      return (
        <div className="mt-2 rounded-lg bg-danger-soft px-3 py-2 text-sm" role="alert">
          <p className="font-medium text-danger">Couldn&apos;t read this resume</p>
          <p className="text-muted">{resume.parse_error}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={onRetry} loading={retrying}>
            Try again
          </Button>
        </div>
      );
  }
}

function RenameForm({ resume, onDone }: { resume: Resume; onDone: () => void }) {
  const rename = useRenameResume();
  const [value, setValue] = useState(resume.name);
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!value.trim()) return setError("Enter a name");
        try {
          await rename.mutateAsync({ id: resume.id, name: value.trim() });
          onDone();
        } catch (err) {
          setError(describeError(err));
        }
      }}
    >
      <input
        aria-label="Resume name"
        value={value}
        maxLength={120}
        autoFocus
        onChange={(event) => setValue(event.target.value)}
        className="h-8 min-w-0 flex-1 rounded-md border border-line-strong bg-surface px-2 text-sm focus:border-primary focus:ring-4 focus:ring-ring focus:outline-none"
      />
      <Button type="submit" size="sm" loading={rename.isPending}>
        Save
      </Button>
      <Button variant="ghost" size="sm" onClick={onDone}>
        Cancel
      </Button>
      {error && <p className="w-full text-xs text-danger">{error}</p>}
    </form>
  );
}
