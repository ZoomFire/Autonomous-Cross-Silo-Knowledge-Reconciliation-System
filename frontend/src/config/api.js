const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();
const defaultApiBaseUrl = import.meta.env.DEV
  ? "http://localhost:8000"
  : "https://autonomous-cross-silo-knowledge.onrender.com";

export const API_BASE_URL = (configuredApiBaseUrl || defaultApiBaseUrl).replace(/\/$/, "");

export function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

if (import.meta.env.DEV) {
  console.log("API_BASE_URL:", API_BASE_URL);
}
