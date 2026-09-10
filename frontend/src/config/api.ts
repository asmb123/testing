const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

/**
 * The only frontend deployment setting for the API host.
 * Examples: http://localhost:8081 or https://api.example.com/api
 */
export const API_BASE_URL = (configuredApiUrl || "http://localhost:8081").replace(/\/+$/, "");

/** Keep every backend endpoint used by the UI in one place. */
export const API_ENDPOINTS = {
  root: "/",
  authMe: "/auth/me",
  fetchRepository: "/fetchrepo",
  reviewReadme: "/review",
} as const;

export function apiUrl(endpoint: string): string {
  return `${API_BASE_URL}${endpoint}`;
}
