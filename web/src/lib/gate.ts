// Cookie gates for /api/* route handlers.
//
// The Next.js proxy only redirects user-facing /pages — same-origin /api/*
// routes (which proxy uploads + LLM calls to FastAPI) need their own check
// or anyone who knows the URL can call them from curl/Postman.
//
// Use one of these at the top of a route handler:
//
//   const denied = await requireLead();
//   if (denied) return denied;
//
//   const denied = await requireAccess();
//   if (denied) return denied;
//
// requireLead unlocks the demo/sample-backed endpoints (recommend, copilot,
// matching, ask). requireAccess unlocks endpoints that operate on the user's
// own uploaded files (diagnostic, docs, map-headers).
//
// Both cookies are HMAC-signed (auth.ts), so a self-granted pk_lead=1 no
// longer passes. requireAccess additionally re-checks the access code that
// is embedded in the cookie against the access_codes table, so revoking a
// code in Supabase revokes that customer's API access immediately.

import { cookies } from "next/headers";
import {
  ACCESS_COOKIE,
  LEAD_COOKIE,
  verifyAccessCookieValue,
  verifyLeadCookieValue,
} from "@/lib/auth";
import { isValidAccessCode } from "@/lib/store";

export async function requireLead(): Promise<Response | null> {
  const value = (await cookies()).get(LEAD_COOKIE)?.value;
  if (await verifyLeadCookieValue(value)) return null;
  return Response.json(
    { error: "Lead capture required. Unlock the sample at /sample." },
    { status: 401 },
  );
}

export async function requireAccess(): Promise<Response | null> {
  const value = (await cookies()).get(ACCESS_COOKIE)?.value;
  const verified = await verifyAccessCookieValue(value);
  if (verified.ok && (await isValidAccessCode(verified.code))) return null;
  return Response.json(
    { error: "Access code required. Sign in at /login." },
    { status: 401 },
  );
}

// The tenant key for the decision log: the verified access code when the
// visitor has one (each design partner gets their own), otherwise "default".
// The exceptions/digest proxies forward this to FastAPI as X-Pricekeel-Customer
// so one lead-gated visitor can never read another customer's logged decisions.
// Lead-only visitors (sample demo, no access code) all share "default", which
// is correct: they are looking at the shared demo book, not customer data.
export async function customerRef(): Promise<string> {
  const value = (await cookies()).get(ACCESS_COOKIE)?.value;
  const verified = await verifyAccessCookieValue(value);
  if (verified.ok && (await isValidAccessCode(verified.code))) {
    return verified.code;
  }
  return "default";
}
