import { api, post } from "@/lib/api-client";
import type { Me } from "@/types/api";

export const getMe = () => api<Me>("/api/auth/me/");
export const login = (username: string, password: string) =>
  post<Me & { csrfToken: string }>("/api/auth/login/", { username, password });
export const logout = () => post<{ ok: boolean }>("/api/auth/logout/");
