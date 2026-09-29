import type { ChangePasswordPayload, User, UserUpdate } from "@/types/api";
import { request } from "@/services/http";

export const usersApi = {
  me: () => request<User>("/users/me"),
  update: (data: UserUpdate) => request<User>("/users/me", { method: "PATCH", body: data }),
  completeOnboarding: () => request<User>("/users/me/onboarding/complete", { method: "POST" }),
  changePassword: (data: ChangePasswordPayload) =>
    request<void>("/users/me/password", { method: "POST", body: data }),
};
