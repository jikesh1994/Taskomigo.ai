"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { preferencesApi } from "@/services/preferences";

export const preferencesKey = ["preferences"] as const;

export function usePreferences() {
  return useQuery({ queryKey: preferencesKey, queryFn: preferencesApi.get });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: preferencesApi.update,
    onSuccess: (preferences) => queryClient.setQueryData(preferencesKey, preferences),
  });
}
