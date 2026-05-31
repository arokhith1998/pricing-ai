// Signed magic-link tokens for lead recovery.
//
// A returning visitor who already submitted the lead form should not have to
// fill it again on a new device or after their cookie expired. The flow:
//
//   1. Visitor enters their email on /sample.
//   2. POST /api/lead/magic-link looks them up in Supabase. If found, emails a
//      short-lived signed URL.
//   3. GET /api/lead/redeem?t=<token> verifies the HMAC, sets pk_lead, and
//      redirects them back into the gated area.
//
// Token shape (URL-safe):
//   base64url("<email>|<exp_unix_seconds>") + "." + base64url(hmac_sha256_bytes)
//
// All-Web-Crypto, so it works equally in Node and Edge runtimes (same pattern
// auth.ts uses for the access cookie).

const MAGIC_TTL_SECONDS = 60 * 60 * 24; // 24 hours

function secret(): string {
  // Same secret the access cookie uses. Set PRICEKEEL_SECRET in production.
  return process.env.PRICEKEEL_SECRET ?? "pricekeel-dev-secret";
}

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
    enc.encode(secret()),
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

/** Create a signed token for `email`, valid for 24 hours. */
export async function makeMagicToken(email: string): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + MAGIC_TTL_SECONDS;
  const payload = `${email.trim().toLowerCase()}|${exp}`;
  const sig = await hmacBytes(payload);
  const enc = new TextEncoder();
  return `${toB64Url(enc.encode(payload))}.${toB64Url(sig)}`;
}

export type MagicVerifyResult =
  | { ok: true; email: string }
  | { ok: false; reason: "malformed" | "expired" | "bad_signature" };

/** Validate a token. Constant-time on the signature compare. */
export async function verifyMagicToken(token: string): Promise<MagicVerifyResult> {
  const parts = token.split(".");
  if (parts.length !== 2) return { ok: false, reason: "malformed" };
  let payload: string;
  let sig: Uint8Array;
  try {
    payload = new TextDecoder().decode(fromB64Url(parts[0]));
    sig = fromB64Url(parts[1]);
  } catch {
    return { ok: false, reason: "malformed" };
  }
  const expected = await hmacBytes(payload);
  if (!constantTimeEqual(sig, expected)) return { ok: false, reason: "bad_signature" };

  const [email, expStr] = payload.split("|");
  if (!email || !expStr) return { ok: false, reason: "malformed" };
  const exp = Number(expStr);
  if (!Number.isFinite(exp) || exp < Math.floor(Date.now() / 1000)) {
    return { ok: false, reason: "expired" };
  }
  return { ok: true, email };
}

/** Build the absolute redeem URL the email links to. */
export function magicRedeemUrl(origin: string, token: string, next?: string): string {
  const u = new URL("/api/lead/redeem", origin);
  u.searchParams.set("t", token);
  if (next) u.searchParams.set("next", next);
  return u.toString();
}
