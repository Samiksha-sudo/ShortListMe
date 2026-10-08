import type { AuthResult } from "./api";

const KEY = "shortlistme.session";

export function loadSession(): AuthResult | null {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "null");
  } catch {
    return null;
  }
}

export function saveSession(s: AuthResult): void {
  localStorage.setItem(KEY, JSON.stringify(s));
}

export function clearSession(): void {
  localStorage.removeItem(KEY);
}
