import { api } from "./api";

const TOKEN_KEY = "omnidrive.token";

export type User = { id: number; created_at: string; updated_at: string };

export const authService = {
  async login(): Promise<{ access_token: string; user: User }> {
    const { data } = await api.post("/auth/session");
    localStorage.setItem(TOKEN_KEY, data.access_token);
    return data;
  },
  async logout(): Promise<void> {
    localStorage.removeItem(TOKEN_KEY);
  },
  async getUser(): Promise<User> {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) throw new Error("not authenticated");
    const { data } = await api.get("/auth/me");
    return data;
  },
};
