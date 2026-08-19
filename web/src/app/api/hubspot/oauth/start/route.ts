import { NextResponse } from "next/server";
import { customerRef, requireAccess } from "@/lib/gate";
import {
  createHubspotOAuthAttempt,
  HUBSPOT_OAUTH_COOKIE,
  hubspotOAuthCookieOptions,
} from "@/lib/hubspot-oauth";

export async function GET(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  const customer = await customerRef();
  if (customer === "default") {
    return Response.json(
      { error: "A customer access code is required." },
      { status: 401 },
    );
  }
  try {
    const attempt = createHubspotOAuthAttempt(customer, req.url);
    const response = NextResponse.redirect(attempt.authorizationUrl);
    response.cookies.set(
      HUBSPOT_OAUTH_COOKIE,
      attempt.cookieValue,
      hubspotOAuthCookieOptions(),
    );
    return response;
  } catch (error) {
    return Response.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "HubSpot OAuth is unavailable.",
      },
      { status: 503 },
    );
  }
}
