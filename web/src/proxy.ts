// Next.js 16 renamed `middleware` to `proxy`. Two-tier funnel gate:
//   public:      /, /sample (teaser), /login, /api/*, static
//   needs lead:  /diagnostic, /guidance  (full sample results)
//   needs code:  /upload, /crm, /competitor-watch (customer workspace)
//
// Cookie checks here are signature-only (no DB round-trip per request).
// Revocation of an access code is enforced by gate.ts on the API routes,
// which re-check the code embedded in the cookie against access_codes.
//
// Demo tenant mint-once (silent-failure-hunter finding 6): gate.ts's
// customerRef() used to mint a fresh demo:<uuid> tenant lazily, in whichever
// route handler first saw a missing pk_demo_tenant cookie. A page load fires
// more than one client-side fetch on mount (e.g. a guidance recommendation
// call and a decision-log read), in parallel, and neither had necessarily
// established the cookie first: two concurrent "first" requests then each
// minted their own tenant id, and the browser kept only the last Set-Cookie
// it received, so decisions already logged under the id that lost became
// unreadable (GET /exceptions filters by the surviving cookie's tenant).
//
// Proxy runs ahead of every request, including the page navigation itself,
// which the browser must finish loading (and apply the resulting Set-Cookie
// to) before any client component mounts and fires its own fetches. Minting
// here, once, on whichever request reaches the server first (in practice the
// page navigation), removes the race in the case that actually occurs in the
// product. The X-Pk-Demo-Tenant request header this sets is the other half of
// the fix: gate.ts's customerRef() reads it instead of re-deriving (or, on a
// proxy gap, re-minting) the tenant from cookies.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  ACCESS_COOKIE,
  DEMO_TENANT_COOKIE,
  DEMO_TENANT_HEADER,
  LEAD_COOKIE,
  demoTenantCookieOptions,
  leadCookieOptions,
  makeDemoTenantCookieValue,
  makeLeadCookieValue,
  verifyAccessCookieValue,
  verifyDemoTenantCookieValue,
  verifyLeadCookieValue,
} from "@/lib/auth";

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // An access-code visitor never needs a demo tenant. Whether the code
  // itself is still valid is a database check (access_codes table) that
  // stays in gate.ts's requireAccess(): Proxy runs on every route, including
  // prefetches, so it must stay an optimistic, cookie-only check here (per
  // the Next.js authentication guide) and never touch Neon.
  let demoTenantId: string | null = null;
  let mintedDemoTenantCookieValue: string | null = null;
  if (!request.cookies.has(ACCESS_COOKIE)) {
    const existingRaw = request.cookies.get(DEMO_TENANT_COOKIE)?.value;
    demoTenantId = existingRaw ? await verifyDemoTenantCookieValue(existingRaw) : null;
    if (existingRaw && !demoTenantId) {
      // Present but does not verify: tampering, or PRICEKEEL_SECRET rotated
      // under a live cookie. This used to fail silently straight into a
      // fresh mint; logging it lets an operator tell a secret rotation (a
      // burst right after a deploy) from an attack (steady trickle) from the
      // volume of these lines.
      console.error(
        "[proxy] pk_demo_tenant cookie failed signature verification; minting a replacement.",
      );
    }
    if (!demoTenantId) {
      demoTenantId = crypto.randomUUID();
      mintedDemoTenantCookieValue = await makeDemoTenantCookieValue(demoTenantId);
    }
  }
  // Forwarded to every `next()` response below so a route handler or server
  // component rendered in THIS SAME request cycle reads the established id
  // instead of re-deriving (or re-minting) it from cookies. Irrelevant on a
  // redirect: a redirect always causes a fresh browser round-trip, which
  // will carry the Set-Cookie applied below and go through proxy again.
  const forwardedHeaders = new Headers(request.headers);
  if (demoTenantId) forwardedHeaders.set(DEMO_TENANT_HEADER, demoTenantId);
  const next = () => NextResponse.next({ request: { headers: forwardedHeaders } });
  const withDemoTenantCookie = (response: NextResponse) => {
    if (mintedDemoTenantCookieValue) {
      response.cookies.set(DEMO_TENANT_COOKIE, mintedDemoTenantCookieValue, demoTenantCookieOptions());
    }
    return response;
  };

  // Their own data: requires a valid access code.
  if (
    pathname.startsWith("/upload") ||
    pathname.startsWith("/crm") ||
    pathname.startsWith("/competitor-watch")
  ) {
    const value = request.cookies.get(ACCESS_COOKIE)?.value;
    if ((await verifyAccessCookieValue(value)).ok) return withDemoTenantCookie(next());
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return withDemoTenantCookie(NextResponse.redirect(url));
  }

  // Full sample results: require a captured lead.
  if (
    pathname.startsWith("/diagnostic") ||
    pathname.startsWith("/guidance")
  ) {
    const value = request.cookies.get(LEAD_COOKIE)?.value;
    if (await verifyLeadCookieValue(value)) {
      // Rolling refresh. An engaged visitor never expires.
      const res = next();
      res.cookies.set(LEAD_COOKIE, await makeLeadCookieValue(), leadCookieOptions());
      return withDemoTenantCookie(res);
    }
    const url = request.nextUrl.clone();
    url.pathname = "/sample";
    url.searchParams.set("unlock", pathname.slice(1));
    return withDemoTenantCookie(NextResponse.redirect(url));
  }

  return withDemoTenantCookie(next());
}
