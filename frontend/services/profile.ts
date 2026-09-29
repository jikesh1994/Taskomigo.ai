import type {
  Education,
  EducationInput,
  Experience,
  ExperienceInput,
  Profile,
  ProfileUpdate,
  Skill,
  SkillInput,
  UUID,
} from "@/types/api";
import { request } from "@/services/http";

export const profileApi = {
  get: () => request<Profile>("/profile"),
  update: (data: ProfileUpdate) => request<Profile>("/profile", { method: "PATCH", body: data }),

  addExperience: (data: ExperienceInput) =>
    request<Experience>("/profile/experiences", { method: "POST", body: data }),
  updateExperience: (id: UUID, data: Partial<ExperienceInput>) =>
    request<Experience>(`/profile/experiences/${id}`, { method: "PATCH", body: data }),
  deleteExperience: (id: UUID) =>
    request<void>(`/profile/experiences/${id}`, { method: "DELETE" }),

  addEducation: (data: EducationInput) =>
    request<Education>("/profile/education", { method: "POST", body: data }),
  updateEducation: (id: UUID, data: Partial<EducationInput>) =>
    request<Education>(`/profile/education/${id}`, { method: "PATCH", body: data }),
  deleteEducation: (id: UUID) => request<void>(`/profile/education/${id}`, { method: "DELETE" }),

  addSkill: (data: SkillInput) => request<Skill>("/profile/skills", { method: "POST", body: data }),
  updateSkill: (id: UUID, data: Partial<SkillInput>) =>
    request<Skill>(`/profile/skills/${id}`, { method: "PATCH", body: data }),
  deleteSkill: (id: UUID) => request<void>(`/profile/skills/${id}`, { method: "DELETE" }),
};
