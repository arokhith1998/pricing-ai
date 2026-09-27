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
// code in the database revokes that customer's API access immediately.

import { cookies } from "next/headers";
import {
  ACCESS_COOKIE,
  DEMO_TENANT_COOKIE,
  LEAD_COOKIE,
  demoTenantCookieOptions,
  makeDemoTenantCookieValue,
  verifyAccessCookieValue,
  verifyDemoTenantCookieValue,
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
// visitor has one (each design partner gets their own), otherwise a signed
// per-visitor demo tenant ("demo:<uuid>"). Every proxy that talks to the
// governance/RAG/rate-limit-scoped backend routes forwards this as
// X-Pricekeel-Customer so one visitor can never read another's logged
// decisions, uploaded docs, or exhaust another visitor's rate-limit bucket.
//
// Lead-only visitors (sample demo, no access code) all look at the same
// shared demo book (book_source "demo") -- that part is intentionally
// shared. Only the decision-log/doc-store tenant is per-visitor: without it,
// visitor A's typed exception justification was readable by visitor B via
// GET /exceptions, because both landed under the same "default" bucket.
export async function customerRef(): Promise<string> {
  const jar = await cookies();
  const accessValue = jar.get(ACCESS_COOKIE)?.value;
  const verified = await verifyAccessCookieValue(accessValue);
  if (verified.ok && (await isValidAccessCode(verified.code))) {
    return verified.code;
  }

  const existing = await verifyDemoTenantCookieValue(jar.get(DEMO_TENANT_COOKIE)?.value);
  if (existing) return `demo:${existing}`;

  const id = crypto.randomUUID();
  jar.set(DEMO_TENANT_COOKIE, await makeDemoTenantCookieValue(id), demoTenantCookieOptions());
  return `demo:${id}`;
}
