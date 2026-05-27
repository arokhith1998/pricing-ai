// Minimal shared-access-code gate for the gated demo. Not user accounts: one
// code, set as PRICEKEEL_ACCESS_CODE, unlocks the whole demo. If the env var is
// unset (e.g. local dev), the gate is OFF and everything is public.
//
// WorkOS / SSO comes later (see docs/design/nextjs-ui.md M3+). This is the
// "email allowlist for the demo" tier, simplified to one shared code.

export const AUTH_COOKIE = "pk_auth";

function accessCode(): string {
  return process.env.PRICEKEEL_ACCESS_CODE ?? "";
}

/** A code is configured, so logins can succeed. */
export function authEnabled(): boolean {
  return accessCode().length > 0;
}

/**
 * Whether the gate is enforced. Fail closed: production ALWAYS enforces, even
 * if PRICEKEEL_ACCESS_CODE was forgotten (then no login can succeed and the app
 * is locked, rather than silently public). Local dev is open when no code set.
 */
export function gateActive(): boolean {
  return authEnabled() || process.env.NODE_ENV === "production";
}

/** Opaque cookie token derived from the code (so we never store it in plain). */
export async function expectedToken(): Promise<string> {
  const data = new TextEncoder().encode(`pricekeel:${accessCode()}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function isValidCode(input: string): boolean {
  return authEnabled() && input === accessCode();
}
