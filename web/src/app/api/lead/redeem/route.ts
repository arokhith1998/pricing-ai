// GET /api/lead/redeem?t=<token>&next=<route>
//
// Validates the magic-link token, sets the pk_lead cookie, then redirects.
// On failure, redirects to /sample with a flash query param so the page can
// explain (expired link, etc).
//
// Token is HMAC-signed by /api/lead/magic-link with a 24-hour expiry.

import { NextResponse } from "next/server";
import { LEAD_COOKIE, leadCookieOptions, makeLeadCookieValue } from "@/lib/auth";
import { verifyMagicToken } from "@/lib/magic";

const ALLOWED_NEXT = new Set([
  "/sample",
  "/diagnostic",
  "/guidance",
  "/competitor-watch",
]);

export async function GET(req: Request) {
  const url = new URL(req.url);
  const token = url.searchParams.get("t") || "";
  const nextRaw = url.searchParams.get("next") || "";
  const next = ALLOWED_NEXT.has(nextRaw) ? nextRaw : "/sample";

  const result = await verifyMagicToken(token);
  if (!result.ok) {
    const flash = result.reason === "expired" ? "link_expired" : "link_invalid";
    return NextResponse.redirect(new URL(`/sample?flash=${flash}`, url.origin), 302);
  }

  // Use NextResponse.redirect + res.cookies.set so the Set-Cookie header
  // actually rides on the redirect response. The cookies() helper from
  // next/headers does not attach to native Response.redirect().
  const res = NextResponse.redirect(new URL(next, url.origin), 302);
  res.cookies.set(LEAD_COOKIE, await makeLeadCookieValue(), leadCookieOptions());
  return res;
}
