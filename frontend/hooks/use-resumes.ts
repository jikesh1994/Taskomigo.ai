"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileKey } from "@/hooks/use-profile";
import { resumesApi } from "@/services/resumes";
import type { Resume, ReviewAction } from "@/types/api";

export const resumesKey = ["resumes"] as const;
export const reviewKey = (id: string) => ["resumes", id, "review"] as const;

const isWorking = (r: Resume) => r.parse_status === "pending" || r.parse_status === "processing";

export function useResumes() {
  return useQuery({
    queryKey: resumesKey,
    queryFn: resumesApi.list,
    // Parsing happens in the background; poll until every resume has settled.
    refetchInterval: (query) => (query.state.data?.some(isWorking) ? 2000 : false),
  });
}

export function useResumeReview(id: string | null, enabled = true) {
  return useQuery({
    queryKey: reviewKey(id ?? "none"),
    queryFn: () => resumesApi.review(id!),
    enabled: Boolean(id) && enabled,
  });
}

function useResumeMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: resumesKey }),
  });
}

export const useUploadResume = () =>
  useResumeMutation(({ file, name }: { file: File; name?: string }) => resumesApi.upload(file, name));
export const useRenameResume = () =>
  useResumeMutation(({ id, name }: { id: string; name: string }) => resumesApi.update(id, { name }));
export const useMakeDefaultResume = () =>
  useResumeMutation((id: string) => resumesApi.update(id, { is_default: true }));
export const useDeleteResume = () => useResumeMutation(resumesApi.remove);
export const useReparseResume = () => useResumeMutation(resumesApi.reparse);

export function useApplyReview(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (decisions: { id: string; action: ReviewAction }[]) => resumesApi.applyReview(id, decisions),
    onSuccess: async (result) => {
      queryClient.setQueryData(reviewKey(id), result.review);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: profileKey }),
        queryClient.invalidateQueries({ queryKey: resumesKey, exact: true }),
      ]);
    },
  });
}
