import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { customerRef } from "@/lib/gate";
import {
  exchangeHubspotCode,
  HUBSPOT_API_BASE,
  HUBSPOT_OAUTH_COOKIE,
  hubspotExpiryIso,
  hubspotIdentity,
  hubspotOAuthCookieOptions,
  verifyHubspotOAuthAttempt,
} from "@/lib/hubspot-oauth";
import { saveHubspotConnection } from "@/lib/hubspot-store";

function crmRedirect(req: Request, key: "connected" | "error", value: string) {
  const url = new URL("/crm", req.url);
  url.searchParams.set(key, value);
  return NextResponse.redirect(url);
}

function clearAttempt(response: NextResponse) {
  response.cookies.set(HUBSPOT_OAUTH_COOKIE, "", {
    ...hubspotOAuthCookieOptions(),
    maxAge: 0,
  });
  return response;
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const oauthError = url.searchParams.get("error");
  if (oauthError) {
    return clearAttempt(crmRedirect(req, "error", "authorization_denied"));
  }
  const code = url.searchParams.get("code") ?? "";
  const state = url.searchParams.get("state") ?? "";
  const cookieStore = await cookies();
  const attemptCookie = cookieStore.get(HUBSPOT_OAUTH_COOKIE)?.value ?? "";
  const customer = await customerRef();
  const attempt = verifyHubspotOAuthAttempt(state, attemptCookie, customer);
  if (!code || customer === "default" || !attempt) {
    return clearAttempt(crmRedirect(req, "error", "invalid_oauth_state"));
  }
  try {
    const token = await exchangeHubspotCode(code, req.url);
    const identity = await hubspotIdentity(token.access_token);
    await saveHubspotConnection({
      customer_ref: customer,
      // org_id carries the HubSpot portal ID, the tenant identity on their
      // side. instance_url carries the fixed API base: HubSpot has no
      // per-customer host, unlike a Salesforce instance URL.
      org_id: identity.portalId,
      user_id: identity.userId,
      instance_url: HUBSPOT_API_BASE,
      access_token: token.access_token,
      refresh_token: token.refresh_token ?? "",
      token_type: token.token_type,
      scope: identity.scopes.join(" "),
      // issued_at holds the absolute expiry, so the client can refresh ahead
      // of the 30-minute access-token lifetime instead of only on a 401.
      issued_at: hubspotExpiryIso(token),
    });
    return clearAttempt(crmRedirect(req, "connected", "1"));
  } catch {
    return clearAttempt(crmRedirect(req, "error", "token_exchange_failed"));
  }
}
