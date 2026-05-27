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

export function authEnabled(): boolean {
  return accessCode().length > 0;
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
