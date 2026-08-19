import "server-only";

import { randomBytes } from "node:crypto";
import { signCrmState, verifyCrmState } from "@/lib/crm-crypto";

// HubSpot OAuth 2.0, slice 2 of docs/design/hubspot-crm-integration.md.
//
// Deliberately an OAuth public app (installed by direct link, no App
// Marketplace listing required) rather than a private app. HubSpot documents
// private-app tokens as unsuitable for third-party vendors: the token carries
// the access of the user who created it and stops working when that person
// leaves the account, which for us is a silent outage with no recovery path we
// control. HubSpot has also moved private apps under "Legacy apps".
//
// Difference from the Salesforce flow worth stating out loud: HubSpot does not
// support PKCE, so there is no code verifier here. That is not an oversight.
// The CSRF defence is the same one Salesforce relies on independently of PKCE:
// a signed state carrying a nonce, matched against a signed httpOnly cookie
// bound to the same tenant, both short-lived. The registered redirect_uri and
// the client secret are the compensating controls for the missing verifier.

export const HUBSPOT_OAUTH_COOKIE = "pk_hs_oauth";
export const HUBSPOT_OAUTH_MAX_AGE_SECONDS = 10 * 60;

export const HUBSPOT_AUTHORIZE_URL = "https://app.hubspot.com/oauth/authorize";
export const HUBSPOT_API_BASE = "https://api.hubapi.com";

// Read-only by design. Slice 2 connects and reads; nothing in the HubSpot
// integration writes back yet, so no write scope is requested. Asking for less
// is also what makes the install dialog survive a security review.
export const HUBSPOT_SCOPES = [
  "oauth",
  "crm.objects.deals.read",
  "crm.objects.line_items.read",
  "crm.objects.companies.read",
  "crm.objects.owners.read",
  "crm.schemas.deals.read",
] as const;

type OAuthState = {
  customer: string;
  nonce: string;
  exp: number;
};

export type HubspotTokenResponse = {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
};

export type HubspotIdentity = {
  portalId: string;
  userId: string;
  user: string;
  scopes: string[];
};

function hubspotClientId(): string {
  const value = process.env.HUBSPOT_CLIENT_ID?.trim();
  if (!value) throw new Error("HUBSPOT_CLIENT_ID is not configured.");
  return value;
}

function hubspotClientSecret(): string {
  const value = process.env.HUBSPOT_CLIENT_SECRET?.trim();
  if (!value) throw new Error("HUBSPOT_CLIENT_SECRET is not configured.");
  return value;
}

export function hubspotRedirectUri(requestUrl?: string): string {
  const configured = process.env.HUBSPOT_OAUTH_REDIRECT_URI?.trim();
  if (configured) return configured;
  if (process.env.VERCEL_ENV === "production") {
    throw new Error("HUBSPOT_OAUTH_REDIRECT_URI is required in production.");
  }
  if (!requestUrl) {
    return "http://localhost:3000/api/hubspot/oauth/callback";
  }
  return new URL("/api/hubspot/oauth/callback", requestUrl).toString();
}

export function createHubspotOAuthAttempt(
  customer: string,
  requestUrl: string,
): { authorizationUrl: string; cookieValue: string } {
  const state: OAuthState = {
    customer,
    nonce: randomBytes(24).toString("base64url"),
    exp: Math.floor(Date.now() / 1000) + HUBSPOT_OAUTH_MAX_AGE_SECONDS,
  };
  const url = new URL(HUBSPOT_AUTHORIZE_URL);
  url.searchParams.set("client_id", hubspotClientId());
  url.searchParams.set("redirect_uri", hubspotRedirectUri(requestUrl));
  url.searchParams.set("scope", HUBSPOT_SCOPES.join(" "));
  url.searchParams.set("state", signCrmState(state));
  return {
    authorizationUrl: url.toString(),
    cookieValue: signCrmState(state),
  };
}

export function verifyHubspotOAuthAttempt(
  stateValue: string,
  cookieValue: string,
  expectedCustomer: string,
): OAuthState | null {
  const state = verifyCrmState<OAuthState>(stateValue);
  const attempt = verifyCrmState<OAuthState>(cookieValue);
  const now = Math.floor(Date.now() / 1000);
  if (
    !state ||
    !attempt ||
    state.exp < now ||
    attempt.exp < now ||
    state.customer !== expectedCustomer ||
    attempt.customer !== expectedCustomer ||
    state.nonce !== attempt.nonce
  ) {
    return null;
  }
  return attempt;
}

async function postTokenRequest(
  body: URLSearchParams,
  failureLabel: string,
): Promise<HubspotTokenResponse> {
  const response = await fetch(`${HUBSPOT_API_BASE}/oauth/v1/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${failureLabel} (${response.status}).`);
  }
  const token = (await response.json()) as HubspotTokenResponse;
  if (!token.access_token) {
    throw new Error(`${failureLabel}: no access token returned.`);
  }
  return token;
}

export async function exchangeHubspotCode(
  code: string,
  requestUrl: string,
): Promise<HubspotTokenResponse> {
  const token = await postTokenRequest(
    new URLSearchParams({
      grant_type: "authorization_code",
      code,
      client_id: hubspotClientId(),
      client_secret: hubspotClientSecret(),
      redirect_uri: hubspotRedirectUri(requestUrl),
    }),
    "HubSpot token exchange failed",
  );
  if (!token.refresh_token) {
    // Without a refresh token the connection dies in 30 minutes and cannot
    // recover unattended. Fail the connect rather than store something that
    // looks connected and silently stops working.
    throw new Error(
      "HubSpot did not return a refresh token, so the connection would not survive access-token expiry.",
    );
  }
  return token;
}

export async function refreshHubspotToken(
  refreshToken: string,
): Promise<HubspotTokenResponse> {
  return postTokenRequest(
    new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: hubspotClientId(),
      client_secret: hubspotClientSecret(),
    }),
    "HubSpot token refresh failed",
  );
}

// HubSpot access tokens are short-lived (expires_in is typically 1800s). We
// persist the absolute expiry so a caller can refresh before a request rather
// than only reacting to a 401.
export function hubspotExpiryIso(token: HubspotTokenResponse): string {
  const seconds = Number(token.expires_in);
  const lifetime = Number.isFinite(seconds) && seconds > 0 ? seconds : 1800;
  return new Date(Date.now() + lifetime * 1000).toISOString();
}

export async function hubspotIdentity(
  accessToken: string,
): Promise<HubspotIdentity> {
  const response = await fetch(
    `${HUBSPOT_API_BASE}/oauth/v1/access-tokens/${encodeURIComponent(accessToken)}`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error(`HubSpot token introspection failed (${response.status}).`);
  }
  const body = (await response.json()) as {
    hub_id?: number | string;
    user?: string;
    user_id?: number | string;
    scopes?: string[];
  };
  const portalId = body.hub_id === undefined ? "" : String(body.hub_id);
  if (!portalId) {
    // The portal ID is the tenant identity on the HubSpot side. Without it we
    // cannot tell two customer portals apart, so this is fatal, not cosmetic.
    throw new Error("HubSpot introspection did not return a portal ID.");
  }
  return {
    portalId,
    userId: body.user_id === undefined ? "" : String(body.user_id),
    user: body.user ?? "",
    scopes: Array.isArray(body.scopes) ? body.scopes : [],
  };
}

export function hubspotOAuthCookieOptions() {
  return {
    httpOnly: true as const,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/api/hubspot/oauth",
    maxAge: HUBSPOT_OAUTH_MAX_AGE_SECONDS,
  };
}

export function hubspotOAuthConfigured(): boolean {
  const productionReady = (value?: string) =>
    Boolean(value?.trim()) || process.env.VERCEL_ENV !== "production";
  return Boolean(
    process.env.HUBSPOT_CLIENT_ID?.trim() &&
      process.env.HUBSPOT_CLIENT_SECRET?.trim() &&
      productionReady(process.env.HUBSPOT_OAUTH_REDIRECT_URI) &&
      productionReady(
        process.env.CRM_TOKEN_ENCRYPTION_KEY ||
          process.env.SALESFORCE_TOKEN_ENCRYPTION_KEY,
      ) &&
      productionReady(process.env.DATABASE_URL),
  );
}
