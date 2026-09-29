"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileApi } from "@/services/profile";
import type { Profile } from "@/types/api";

export const profileKey = ["profile"] as const;

export function useProfile() {
  return useQuery({ queryKey: profileKey, queryFn: profileApi.get });
}

/** Mutations that change the profile aggregate refetch it on success. */
function useProfileMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async (result) => {
      if (isProfile(result)) queryClient.setQueryData(profileKey, result);
      else await queryClient.invalidateQueries({ queryKey: profileKey });
    },
  });
}

function isProfile(value: unknown): value is Profile {
  return typeof value === "object" && value !== null && "experiences" in value && "skills" in value;
}

export const useUpdateProfile = () => useProfileMutation(profileApi.update);

export const useAddExperience = () => useProfileMutation(profileApi.addExperience);
export const useUpdateExperience = () =>
  useProfileMutation((args: { id: string; data: Parameters<typeof profileApi.updateExperience>[1] }) =>
    profileApi.updateExperience(args.id, args.data),
  );
export const useDeleteExperience = () => useProfileMutation(profileApi.deleteExperience);

export const useAddEducation = () => useProfileMutation(profileApi.addEducation);
export const useUpdateEducation = () =>
  useProfileMutation((args: { id: string; data: Parameters<typeof profileApi.updateEducation>[1] }) =>
    profileApi.updateEducation(args.id, args.data),
  );
export const useDeleteEducation = () => useProfileMutation(profileApi.deleteEducation);

export const useAddSkill = () => useProfileMutation(profileApi.addSkill);
export const useUpdateSkill = () =>
  useProfileMutation((args: { id: string; data: Parameters<typeof profileApi.updateSkill>[1] }) =>
    profileApi.updateSkill(args.id, args.data),
  );
export const useDeleteSkill = () => useProfileMutation(profileApi.deleteSkill);
