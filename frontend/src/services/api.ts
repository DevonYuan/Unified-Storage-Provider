import axios from "axios";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BACKEND_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("omnidrive.token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
