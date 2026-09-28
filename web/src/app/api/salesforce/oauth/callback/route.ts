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
  // Every step below used to fold into the same silent "token_exchange_failed"
  // redirect with zero server-side signal (silent-failure-hunter finding 5).
  // Each catch here logs a distinguishable cause code (exchange, origin, key,
  // database_url, save_connection) so an operator does not have to guess
  // which one actually failed; the user-facing redirect is unchanged.
  let token;
  try {
    token = await exchangeSalesforceCode(code, attempt.verifier, req.url);
  } catch (cause) {
    console.error("[salesforce-oauth] callback: cause=exchange", cause);
    return clearAttempt(crmRedirect(req, "error", "token_exchange_failed"));
  }
  let instanceUrl: string;
  try {
    instanceUrl = validatedSalesforceOrigin(token.instance_url);
  } catch (cause) {
    console.error("[salesforce-oauth] callback: cause=origin", cause);
    return clearAttempt(crmRedirect(req, "error", "token_exchange_failed"));
  }
  try {
    const identity = salesforceIdentity(token);
    await saveSalesforceConnection({
      customer_ref: customer,
      org_id: identity.orgId,
      user_id: identity.userId,
      instance_url: instanceUrl,
      access_token: token.access_token,
      refresh_token: token.refresh_token ?? "",
      token_type: token.token_type,
      scope: token.scope,
      issued_at: token.issued_at,
    });
    return clearAttempt(crmRedirect(req, "connected", "1"));
  } catch (cause) {
    // saveSalesforceConnection fails for reasons worth telling apart:
    // SALESFORCE_TOKEN_ENCRYPTION_KEY missing (encryptSalesforceSecret),
    // DATABASE_URL missing/unreachable in production (salesforce-store's
    // db()), or a real Neon write failure.
    const message = cause instanceof Error ? cause.message : String(cause);
    const causeCode = /SALESFORCE_TOKEN_ENCRYPTION_KEY/i.test(message)
      ? "key"
      : /DATABASE_URL/i.test(message)
        ? "database_url"
        : "save_connection";
    console.error(`[salesforce-oauth] callback: cause=${causeCode}`, cause);
    return clearAttempt(crmRedirect(req, "error", "token_exchange_failed"));
  }
}
