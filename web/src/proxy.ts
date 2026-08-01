// Next.js 16 renamed `middleware` to `proxy`. Two-tier funnel gate:
//   public:      /, /sample (teaser), /login, /api/*, static
//   needs lead:  /diagnostic, /guidance  (full sample results)
//   needs code:  /upload                  (their own data)
//
// Cookie checks here are signature-only (no DB round-trip per request).
// Revocation of an access code is enforced by gate.ts on the API routes,
// which re-check the code embedded in the cookie against access_codes.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  ACCESS_COOKIE,
  LEAD_COOKIE,
  leadCookieOptions,
  makeLeadCookieValue,
  verifyAccessCookieValue,
  verifyLeadCookieValue,
} from "@/lib/auth";

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Their own data: requires a valid access code.
  if (pathname.startsWith("/upload") || pathname.startsWith("/crm")) {
    const value = request.cookies.get(ACCESS_COOKIE)?.value;
    if ((await verifyAccessCookieValue(value)).ok) return NextResponse.next();
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Full sample results + competitor watch: require a captured lead.
  if (
    pathname.startsWith("/diagnostic") ||
    pathname.startsWith("/guidance") ||
    pathname.startsWith("/competitor-watch")
  ) {
    const value = request.cookies.get(LEAD_COOKIE)?.value;
    if (await verifyLeadCookieValue(value)) {
      // Rolling refresh. An engaged visitor never expires.
      const res = NextResponse.next();
      res.cookies.set(LEAD_COOKIE, await makeLeadCookieValue(), leadCookieOptions());
      return res;
    }
    const url = request.nextUrl.clone();
    url.pathname = "/sample";
    url.searchParams.set("unlock", pathname.slice(1));
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}
