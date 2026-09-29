"use client";

import { clsx } from "clsx";
import { useDeferredValue, useState } from "react";
import { JobCard } from "@/components/jobs/job-card";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { SelectField, TextField } from "@/components/ui/field";
import { useJobList } from "@/hooks/use-jobs";
import type { JobTab, WorkplaceType } from "@/types/api";

const PAGE_SIZE = 20;

const TABS: { key: JobTab; label: string; empty: string }[] = [
  {
    key: "matches",
    label: "Matches",
    empty: "No matches yet. Run a search, or loosen your job preferences in Settings.",
  },
  { key: "saved", label: "Saved", empty: "Jobs you save appear here." },
  { key: "skipped", label: "Skipped", empty: "Jobs you skip appear here, in case you change your mind." },
  {
    key: "hidden",
    label: "Hidden",
    empty: "Nothing hidden. Jobs your filters remove or that score below your minimum appear here.",
  },
];

const WORKPLACE_OPTIONS = [
  { value: "", label: "Any" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];

const SORT_OPTIONS = [
  { value: "score", label: "Best match" },
  { value: "newest", label: "Newest" },
];

export function JobsBrowser() {
  const [tab, setTab] = useState<JobTab>("matches");
  const [q, setQ] = useState("");
  const [workplace, setWorkplace] = useState<WorkplaceType | "">("");
  const [sort, setSort] = useState<"score" | "newest">("score");
  const [page, setPage] = useState(0);
  const query = useDeferredValue(q.trim());

  const list = useJobList({
    tab,
    q: query || undefined,
    workplace: workplace || undefined,
    sort,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });
  const counts = list.data?.counts;
  const current = TABS.find((t) => t.key === tab)!;

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="Job lists" className="flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            type="button"
            aria-selected={tab === t.key}
            onClick={() => {
              setTab(t.key);
              setPage(0);
            }}
            className={clsx(
              "-mb-px shrink-0 border-b-2 px-3 py-2 text-sm whitespace-nowrap transition-colors",
              "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring",
              tab === t.key ? "border-primary font-medium text-fg" : "border-transparent text-muted hover:text-fg",
            )}
          >
            {t.label}
            {counts && <span className="ml-1.5 text-xs text-muted tabular-nums">{counts[t.key]}</span>}
          </button>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_10rem_10rem]">
        <TextField
          id="job-filter"
          label="Filter"
          placeholder="Title or company"
          value={q}
          onChange={(event) => {
            setQ(event.target.value);
            setPage(0);
          }}
        />
        <SelectField
          id="job-workplace"
          label="Work arrangement"
          options={WORKPLACE_OPTIONS}
          value={workplace}
          onChange={(event) => {
            setWorkplace(event.target.value as WorkplaceType | "");
            setPage(0);
          }}
        />
        <SelectField
          id="job-sort"
          label="Sort by"
          options={SORT_OPTIONS}
          value={sort}
          onChange={(event) => setSort(event.target.value as "score" | "newest")}
        />
      </div>

      <div role="tabpanel" aria-label={current.label}>
        <QueryState query={list}>
          {(data) =>
            data.items.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted">
                {query || workplace ? "No jobs match these filters." : current.empty}
              </p>
            ) : (
              <>
                {tab === "matches" && (
                  <p className="mb-3 text-xs text-muted">
                    Scores show how well each job fits your profile and preferences (minimum{" "}
                    {data.min_match_score}). They aren&apos;t a prediction of interviews or offers.
                  </p>
                )}
                <ul className="space-y-3">
                  {data.items.map((job) => (
                    <li key={job.id}>
                      <JobCard job={job} />
                    </li>
                  ))}
                </ul>
                {data.total > PAGE_SIZE && (
                  <div className="mt-4 flex items-center justify-between text-sm text-muted">
                    <span>
                      {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, data.total)} of {data.total}
                    </span>
                    <span className="flex gap-2">
                      <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
                        Previous
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={(page + 1) * PAGE_SIZE >= data.total}
                        onClick={() => setPage(page + 1)}
                      >
                        Next
                      </Button>
                    </span>
                  </div>
                )}
              </>
            )
          }
        </QueryState>
      </div>
    </div>
  );
}
