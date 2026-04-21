import type { Cashier, POSProfile } from "@/types/pos";

const KEY = "surge:cashier_session";
const TTL_MS = 12 * 60 * 60 * 1000;

interface PersistedSession {
  profile: POSProfile;
  cashier: Cashier;
  loginAt: number;
}

export function saveSession(profile: POSProfile, cashier: Cashier): void {
  try {
    const data: PersistedSession = { profile, cashier, loginAt: Date.now() };
    sessionStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // sessionStorage unavailable (private mode quota)
  }
}

export function loadSession(): { profile: POSProfile; cashier: Cashier } | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as PersistedSession;
    if (Date.now() - data.loginAt > TTL_MS) {
      sessionStorage.removeItem(KEY);
      return null;
    }
    return { profile: data.profile, cashier: data.cashier };
  } catch {
    return null;
  }
}

export function clearSession(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
