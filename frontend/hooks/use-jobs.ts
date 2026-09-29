"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isSearchActive, jobSourcesApi, jobsApi } from "@/services/jobs";
import type { JobListParams, JobMatchStatus } from "@/types/api";

export const jobsKey = ["jobs"] as const;
export const jobListKey = (params: JobListParams) => ["jobs", "list", params] as const;
export const jobKey = (id: string) => ["jobs", "detail", id] as const;
export const searchKey = ["jobs", "search"] as const;
export const statsKey = ["jobs", "stats"] as const;
export const sourcesKey = ["job-sources"] as const;
export const catalogKey = ["job-sources", "catalog"] as const;

export function useJobList(params: JobListParams) {
  return useQuery({
    queryKey: jobListKey(params),
    queryFn: () => jobsApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useJob(id: string) {
  const query = useQuery({
    queryKey: jobKey(id),
    queryFn: () => jobsApi.get(id),
    // AI analysis runs in the background; poll until it settles.
    refetchInterval: (q) =>
      q.state.data?.analysis_status === "pending" || q.state.data?.analysis_status === "processing"
        ? 2000
        : false,
  });
  return query;
}

export function useJobStats() {
  return useQuery({ queryKey: statsKey, queryFn: jobsApi.stats });
}

/** The latest search run, polled while it's running. Refreshes job lists when it ends. */
export function useLatestSearch() {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: searchKey,
    queryFn: async () => {
      const previous = queryClient.getQueryData<Awaited<ReturnType<typeof jobsApi.latestSearch>>>(searchKey);
      const run = await jobsApi.latestSearch();
      if (isSearchActive(previous) && !isSearchActive(run)) {
        void queryClient.invalidateQueries({ queryKey: jobsKey, predicate: (q) => q.queryKey[1] !== "search" });
        void queryClient.invalidateQueries({ queryKey: sourcesKey });
      }
      return run;
    },
    refetchInterval: (q) => (isSearchActive(q.state.data) ? 1500 : false),
  });
}

export function useStartSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: jobsApi.search,
    onSuccess: (run) => {
      queryClient.setQueryData(searchKey, run);
      if (!isSearchActive(run)) {
        // Finished inline (dev/test): refresh straight away.
        void queryClient.invalidateQueries({ queryKey: jobsKey, predicate: (q) => q.queryKey[1] !== "search" });
        void queryClient.invalidateQueries({ queryKey: sourcesKey });
      }
    },
  });
}

export function useSetJobStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: JobMatchStatus }) => jobsApi.setStatus(id, status),
    onSuccess: (job) => {
      queryClient.setQueryData(jobKey(job.id), job);
      void queryClient.invalidateQueries({ queryKey: ["jobs", "list"] });
      void queryClient.invalidateQueries({ queryKey: statsKey });
    },
  });
}

export function useAnalyzeJob(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => jobsApi.analyze(id),
    onSuccess: (job) => queryClient.setQueryData(jobKey(id), job),
  });
}

export function useRematch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: jobsApi.rematch,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobsKey, predicate: (q) => q.queryKey[1] !== "search" }),
  });
}

export function useJobSources() {
  return useQuery({ queryKey: sourcesKey, queryFn: jobSourcesApi.list });
}

export function useSourceCatalog() {
  return useQuery({ queryKey: catalogKey, queryFn: jobSourcesApi.catalog });
}

function useSourceMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sourcesKey });
      void queryClient.invalidateQueries({ queryKey: jobsKey, predicate: (q) => q.queryKey[1] !== "search" });
    },
  });
}

export const useAddSource = () => useSourceMutation(jobSourcesApi.add);
export const useRemoveSource = () => useSourceMutation(jobSourcesApi.remove);
export const useToggleSource = () =>
  useSourceMutation(({ id, enabled }: { id: string; enabled: boolean }) => jobSourcesApi.setEnabled(id, enabled));
