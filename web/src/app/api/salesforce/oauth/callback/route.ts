import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { customerRef } from "@/lib/gate";
import { validatedSalesforceOrigin } from "@/lib/salesforce-client";
import {
  exchangeSalesforceCode,
  SALESFORCE_OAUTH_COOKIE,
  salesforceIdentity,
  salesforceOAuthCookieOptions,
  verifySalesforceOAuthAttempt,
} from "@/lib/salesforce-oauth";
import { saveSalesforceConnection } from "@/lib/salesforce-store";

function crmRedirect(req: Request, key: "connected" | "error", value: string) {
  const url = new URL("/crm", req.url);
  url.searchParams.set(key, value);
  return NextResponse.redirect(url);
}

function clearAttempt(response: NextResponse) {
  response.cookies.set(SALESFORCE_OAUTH_COOKIE, "", {
    ...salesforceOAuthCookieOptions(),
    maxAge: 0,
  });
  return response;
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const oauthError = url.searchParams.get("error");
  if (oauthError) return clearAttempt(crmRedirect(req, "error", "authorization_denied"));
  const code = url.searchParams.get("code") ?? "";
  const state = url.searchParams.get("state") ?? "";
  const cookieStore = await cookies();
  const attemptCookie = cookieStore.get(SALESFORCE_OAUTH_COOKIE)?.value ?? "";
  const customer = await customerRef();
  const attempt = verifySalesforceOAuthAttempt(state, attemptCookie, customer);
  if (!code || customer === "default" || !attempt) {
    return clearAttempt(crmRedirect(req, "error", "invalid_oauth_state"));
  }
  try {
    const token = await exchangeSalesforceCode(code, attempt.verifier, req.url);
    const identity = salesforceIdentity(token);
    await saveSalesforceConnection({
      customer_ref: customer,
      org_id: identity.orgId,
      user_id: identity.userId,
      instance_url: validatedSalesforceOrigin(token.instance_url),
      access_token: token.access_token,
      refresh_token: token.refresh_token ?? "",
      token_type: token.token_type,
      scope: token.scope,
      issued_at: token.issued_at,
    });
    return clearAttempt(crmRedirect(req, "connected", "1"));
  } catch {
    return clearAttempt(crmRedirect(req, "error", "token_exchange_failed"));
  }
}
