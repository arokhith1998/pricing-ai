// Two-tier funnel gate (see docs/design/buyer-funnel.md):
//  - pk_lead  : set after a valid lead form. Unlocks the full sample.
//  - pk_access: set after a valid access code. Unlocks /upload (own data).
// The sample is intentionally non-sensitive, so pk_lead is a presence marker.
// pk_access is a stateless token derived from a server secret, so the proxy can
// validate it without a DB round-trip on every request.

export const LEAD_COOKIE = "pk_lead";
export const ACCESS_COOKIE = "pk_access";

// Free / personal email domains we reject for lead capture (company email only).
const FREE_EMAIL_DOMAINS = new Set([
  "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "outlook.com",
  "hotmail.com", "live.com", "msn.com", "icloud.com", "me.com", "mac.com",
  "aol.com", "proton.me", "protonmail.com", "pm.me", "gmx.com", "mail.com",
  "yandex.com", "zoho.com", "hey.com", "fastmail.com",
]);

export function isCompanyEmail(email: string): boolean {
  const m = /^[^\s@]+@([^\s@]+\.[^\s@]+)$/.exec(email.trim().toLowerCase());
  if (!m) return false;
  return !FREE_EMAIL_DOMAINS.has(m[1]);
}

function secret(): string {
  // Set PRICEKEEL_SECRET in production; a constant is fine for local dev.
  return process.env.PRICEKEEL_SECRET ?? "pricekeel-dev-secret";
}

/** Stateless access cookie token, derived from the server secret. */
export async function accessToken(): Promise<string> {
  const data = new TextEncoder().encode(`pricekeel-access:${secret()}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
