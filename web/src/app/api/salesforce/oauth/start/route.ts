import { NextResponse } from "next/server";
import { customerRef, requireAccess } from "@/lib/gate";
import {
  createSalesforceOAuthAttempt,
  SALESFORCE_OAUTH_COOKIE,
  salesforceOAuthCookieOptions,
} from "@/lib/salesforce-oauth";

export async function GET(req: Request) {
  const denied = await requireAccess();
  if (denied) return denied;
  const customer = await customerRef();
  if (customer === "default") {
    return Response.json({ error: "A customer access code is required." }, { status: 401 });
  }
  try {
    const attempt = createSalesforceOAuthAttempt(customer, req.url);
    const response = NextResponse.redirect(attempt.authorizationUrl);
    response.cookies.set(
      SALESFORCE_OAUTH_COOKIE,
      attempt.cookieValue,
      salesforceOAuthCookieOptions(),
    );
    return response;
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Salesforce OAuth is unavailable." },
      { status: 503 },
    );
  }
}
