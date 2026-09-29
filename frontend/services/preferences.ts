import type { Preferences, PreferencesUpdate } from "@/types/api";
import { request } from "@/services/http";

export const preferencesApi = {
  get: () => request<Preferences>("/preferences"),
  update: (data: PreferencesUpdate) =>
    request<Preferences>("/preferences", { method: "PATCH", body: data }),
};
