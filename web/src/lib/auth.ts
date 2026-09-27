// Two-tier funnel gate (see docs/design/buyer-funnel.md):
//  - pk_lead  : set after a valid lead form. Unlocks the full sample.
//  - pk_access: set after a valid access code. Unlocks /upload (own data).
// Both cookies are HMAC-signed with the server secret (same Web Crypto
// pattern magic.ts uses for magic-link tokens), so the proxy can validate
// them without a DB round-trip on every request:
//  - pk_lead  : signed fixed payload ("this visitor passed the lead form").
//  - pk_access: signed payload embedding the access code + an expiry, so the
//    cookie carries per-customer identity and revoking a code in the
//    access_codes table actually revokes that customer (gate.ts re-checks
//    the embedded code against the table on API calls).
//  - pk_demo_tenant: signed payload embedding a random per-visitor id, minted
//    the first time a lead-gated visitor's customerRef() is read (gate.ts).
//    The shared demo book (book_source "demo") stays shared; only the
//    decision-log tenant is per-visitor, so one lead-gated visitor's typed
//    justification is never readable by another via GET /exceptions.

export const LEAD_COOKIE = "pk_lead";
export const ACCESS_COOKIE = "pk_access";
export const DEMO_TENANT_COOKIE = "pk_demo_tenant";

// Request header src/proxy.ts forwards downstream once it has established
// (read or minted) a demo tenant id for the current request, carrying the raw
// id (not the signed cookie value). gate.ts's customerRef() trusts this header
// ahead of re-deriving the tenant from cookies, which is what makes a single
// page load's parallel client-side fetches share one tenant instead of each
// independently minting its own the first time the pk_demo_tenant cookie is
// missing (see proxy.ts's module doc for the full race description).
export const DEMO_TENANT_HEADER = "x-pk-demo-tenant";

// Shared cookie settings for pk_lead. The value is a signed intent marker
// ("this visitor passed the lead form at some point"), not an auth token,
// so a long lifetime is fine. We refresh it on every gated visit in the
// proxy so an engaged user effectively never expires.
export const LEAD_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365; // 1 year

export const ACCESS_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // one week

export const leadCookieOptions = () => ({
  httpOnly: true as const,
  sameSite: "lax" as const,
  path: "/",
  secure: process.env.NODE_ENV === "production",
  maxAge: LEAD_COOKIE_MAX_AGE_SECONDS,
});

export const accessCookieOptions = () => ({
  httpOnly: true as const,
  sameSite: "lax" as const,
  path: "/",
  secure: process.env.NODE_ENV === "production",
  maxAge: ACCESS_COOKIE_MAX_AGE_SECONDS,
});

// Same lifetime as pk_lead: it identifies the same visitor for as long as
// the lead cookie does, so the two should not drift apart.
export const DEMO_TENANT_COOKIE_MAX_AGE_SECONDS = LEAD_COOKIE_MAX_AGE_SECONDS;

export const demoTenantCookieOptions = () => ({
  httpOnly: true as const,
  sameSite: "lax" as const,
  path: "/",
  secure: process.env.NODE_ENV === "production",
  maxAge: DEMO_TENANT_COOKIE_MAX_AGE_SECONDS,
});

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

/** Server secret for cookie/token signing.
 *  Fail-fast on Vercel production: a missing PRICEKEEL_SECRET would silently
 *  sign every customer cookie with a public dev constant. Local dev keeps the
 *  constant fallback so build/verify is never blocked. */
export function pricekeelSecret(): string {
  const s = process.env.PRICEKEEL_SECRET;
  if (s) return s;
  if (process.env.VERCEL_ENV === "production") {
    throw new Error(
      "PRICEKEEL_SECRET is not set. Refusing to sign auth cookies with the dev fallback in production. Set PRICEKEEL_SECRET in the Vercel environment.",
    );
  }
  return "pricekeel-dev-secret";
}

// ---------------------------------------------------------------------------
// Signed cookie values. All-Web-Crypto so the same code runs in the proxy
// (edge-compatible) and in route handlers. Token shape mirrors magic.ts:
//   base64url(payload) + "." + base64url(hmac_sha256_bytes)
// ---------------------------------------------------------------------------

function toB64Url(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromB64Url(s: string): Uint8Array {
  const pad = s.length % 4 ? "=".repeat(4 - (s.length % 4)) : "";
  const b64 = (s + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmacBytes(payload: string): Promise<Uint8Array> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(pricekeelSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  return new Uint8Array(sig);
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

async function signPayload(payload: string): Promise<string> {
  const sig = await hmacBytes(payload);
  return `${toB64Url(new TextEncoder().encode(payload))}.${toB64Url(sig)}`;
}

/** Verify a signed value; returns the payload string or null. */
async function verifySigned(value: string): Promise<string | null> {
  const parts = value.split(".");
  if (parts.length !== 2) return null;
  let payload: string;
  let sig: Uint8Array;
  try {
    payload = new TextDecoder().decode(fromB64Url(parts[0]));
    sig = fromB64Url(parts[1]);
  } catch {
    return null;
  }
  const expected = await hmacBytes(payload);
  return constantTimeEqual(sig, expected) ? payload : null;
}

// --- pk_lead -----------------------------------------------------------------

const LEAD_PAYLOAD = "pricekeel-lead:v1";

/** Signed pk_lead cookie value. Fixed payload: the cookie only attests
 *  "passed the lead form", it carries no identity. */
export async function makeLeadCookieValue(): Promise<string> {
  return signPayload(LEAD_PAYLOAD);
}

export async function verifyLeadCookieValue(
  value: string | undefined,
): Promise<boolean> {
  if (!value) return false;
  return (await verifySigned(value)) === LEAD_PAYLOAD;
}

// --- pk_access ---------------------------------------------------------------

const ACCESS_PREFIX = "pricekeel-access:v1";

/** Signed pk_access cookie value embedding the access code and an expiry.
 *  Per-customer: revoking the code in access_codes invalidates this cookie
 *  wherever the code is re-checked (gate.ts requireAccess). */
export async function makeAccessCookieValue(code: string): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + ACCESS_COOKIE_MAX_AGE_SECONDS;
  return signPayload(`${ACCESS_PREFIX}|${code}|${exp}`);
}

/** Verify signature + expiry and extract the embedded access code. */
export async function verifyAccessCookieValue(
  value: string | undefined,
): Promise<{ ok: true; code: string } | { ok: false }> {
  if (!value) return { ok: false };
  const payload = await verifySigned(value);
  if (!payload) return { ok: false };
  const parts = payload.split("|");
  if (parts.length !== 3 || parts[0] !== ACCESS_PREFIX) return { ok: false };
  const [, code, expStr] = parts;
  const exp = Number(expStr);
  if (!code || !Number.isFinite(exp) || exp < Math.floor(Date.now() / 1000)) {
    return { ok: false };
  }
  return { ok: true, code };
}

// --- pk_demo_tenant ------------------------------------------------------

const DEMO_TENANT_PREFIX = "pricekeel-demo-tenant:v1";

/** Signed pk_demo_tenant cookie value embedding a random per-visitor id.
 *  No expiry check on read (unlike pk_access): a demo tenant id carries no
 *  privilege, it only partitions the shared demo book's decision log so two
 *  visitors never read each other's typed exception requests. */
export async function makeDemoTenantCookieValue(id: string): Promise<string> {
  return signPayload(`${DEMO_TENANT_PREFIX}|${id}`);
}

/** Verify signature and extract the embedded demo tenant id, or null. */
export async function verifyDemoTenantCookieValue(
  value: string | undefined,
): Promise<string | null> {
  if (!value) return null;
  const payload = await verifySigned(value);
  if (!payload) return null;
  const parts = payload.split("|");
  if (parts.length !== 2 || parts[0] !== DEMO_TENANT_PREFIX || !parts[1]) return null;
  return parts[1];
}
