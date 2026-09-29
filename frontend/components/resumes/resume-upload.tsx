"use client";

import { clsx } from "clsx";
import { useId, useRef, useState, type DragEvent } from "react";
import { FormError } from "@/components/forms/form-actions";
import { Spinner } from "@/components/ui/spinner";
import { useUploadResume } from "@/hooks/use-resumes";
import { describeError } from "@/services/errors";
import { RESUME_ACCEPT, validateResumeFile } from "@/services/resumes";

/** Drag-and-drop (or click) upload of one PDF/DOCX resume. */
export function ResumeUpload({ compact = false }: { compact?: boolean }) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const upload = useUploadResume();
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const handle = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    const problem = validateResumeFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    try {
      await upload.mutateAsync({ file });
    } catch (err) {
      setError(describeError(err));
    } finally {
      if (input.current) input.current.value = "";
    }
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    void handle(event.dataTransfer.files[0]);
  };

  return (
    <div className="space-y-3">
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={clsx(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 text-center transition-colors",
          "focus-within:border-primary focus-within:ring-4 focus-within:ring-ring",
          compact ? "py-6" : "py-10",
          dragging ? "border-primary bg-primary-soft" : "border-line-strong bg-surface-2/50 hover:border-primary",
          upload.isPending && "pointer-events-none opacity-70",
        )}
      >
        {upload.isPending ? (
          <>
            <Spinner className="size-6 text-primary" />
            <span className="text-sm font-medium">Uploading…</span>
          </>
        ) : (
          <>
            <svg viewBox="0 0 24 24" className="size-8 text-primary" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
              <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="text-sm font-medium">
              <span className="text-primary">Choose a file</span> or drag it here
            </span>
            <span className="text-xs text-muted">PDF or Word (.docx), up to 5 MB</span>
          </>
        )}
        <input
          ref={input}
          id={inputId}
          type="file"
          accept={RESUME_ACCEPT}
          className="sr-only"
          aria-label="Upload a resume"
          onChange={(event) => void handle(event.target.files?.[0])}
          disabled={upload.isPending}
        />
      </label>
      <FormError message={error} />
    </div>
  );
}
