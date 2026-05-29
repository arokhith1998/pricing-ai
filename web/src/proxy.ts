// Next.js 16 renamed `middleware` to `proxy`. Two-tier funnel gate:
//   public:      /, /sample (teaser), /login, /api/*, static
//   needs lead:  /diagnostic, /guidance  (full sample results)
//   needs code:  /upload                  (their own data)
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { ACCESS_COOKIE, LEAD_COOKIE, accessToken } from "@/lib/auth";

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Their own data: requires a valid access code.
  if (pathname.startsWith("/upload")) {
    const token = request.cookies.get(ACCESS_COOKIE)?.value;
    if (token && token === (await accessToken())) return NextResponse.next();
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
    if (request.cookies.get(LEAD_COOKIE)?.value) return NextResponse.next();
    const url = request.nextUrl.clone();
    url.pathname = "/sample";
    url.searchParams.set("unlock", pathname.slice(1));
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}
