/**
 * Small shared helper around the localStorage-held session token used by
 * every authenticated page. Kept intentionally tiny (no context/provider)
 * to match the pattern already established in the Phase 0/1 dashboard page.
 */
export const TOKEN_KEY = "findback_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
