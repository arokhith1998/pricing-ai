import "server-only";

import { createHash, randomBytes } from "node:crypto";
import {
  signSalesforceState,
  verifySalesforceState,
} from "@/lib/salesforce-crypto";

export const SALESFORCE_OAUTH_COOKIE = "pk_sf_oauth";
export const SALESFORCE_OAUTH_MAX_AGE_SECONDS = 10 * 60;

type OAuthState = {
  customer: string;
  nonce: string;
  exp: number;
};

type OAuthAttempt = OAuthState & {
  verifier: string;
};

export type SalesforceTokenResponse = {
  access_token: string;
  refresh_token?: string;
  instance_url: string;
  id?: string;
  token_type?: string;
  issued_at?: string;
  scope?: string;
};

function salesforceClientId(): string {
  const value = process.env.SALESFORCE_CLIENT_ID?.trim();
  if (!value) throw new Error("SALESFORCE_CLIENT_ID is not configured.");
  return value;
}

function salesforceClientSecret(): string {
  const value = process.env.SALESFORCE_CLIENT_SECRET?.trim();
  if (!value) throw new Error("SALESFORCE_CLIENT_SECRET is not configured.");
  return value;
}

export function salesforceLoginUrl(): string {
  const raw =
    process.env.SALESFORCE_LOGIN_URL?.trim() || "https://login.salesforce.com";
  const url = new URL(raw);
  const allowed =
    url.protocol === "https:" &&
    (url.hostname === "login.salesforce.com" ||
      url.hostname === "test.salesforce.com" ||
      url.hostname.endsWith(".my.salesforce.com"));
  if (!allowed || url.username || url.password) {
    throw new Error("SALESFORCE_LOGIN_URL must be an HTTPS Salesforce login host.");
  }
  return url.origin;
}

export function salesforceRedirectUri(requestUrl?: string): string {
  const configured = process.env.SALESFORCE_OAUTH_REDIRECT_URI?.trim();
  if (configured) return configured;
  if (process.env.VERCEL_ENV === "production") {
    throw new Error("SALESFORCE_OAUTH_REDIRECT_URI is required in production.");
  }
  if (!requestUrl) {
    return "http://localhost:3000/api/salesforce/oauth/callback";
  }
  return new URL("/api/salesforce/oauth/callback", requestUrl).toString();
}

function pkceChallenge(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

export function createSalesforceOAuthAttempt(
  customer: string,
  requestUrl: string,
): { authorizationUrl: string; cookieValue: string } {
  const verifier = randomBytes(48).toString("base64url");
  const state: OAuthState = {
    customer,
    nonce: randomBytes(24).toString("base64url"),
    exp: Math.floor(Date.now() / 1000) + SALESFORCE_OAUTH_MAX_AGE_SECONDS,
  };
  const attempt: OAuthAttempt = { ...state, verifier };
  const url = new URL("/services/oauth2/authorize", salesforceLoginUrl());
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", salesforceClientId());
  url.searchParams.set("redirect_uri", salesforceRedirectUri(requestUrl));
  url.searchParams.set("scope", "api refresh_token");
  url.searchParams.set("state", signSalesforceState(state));
  url.searchParams.set("code_challenge", pkceChallenge(verifier));
  url.searchParams.set("code_challenge_method", "S256");
  return {
    authorizationUrl: url.toString(),
    cookieValue: signSalesforceState(attempt),
  };
}

export function verifySalesforceOAuthAttempt(
  stateValue: string,
  cookieValue: string,
  expectedCustomer: string,
): OAuthAttempt | null {
  const state = verifySalesforceState<OAuthState>(stateValue);
  const attempt = verifySalesforceState<OAuthAttempt>(cookieValue);
  const now = Math.floor(Date.now() / 1000);
  if (
    !state ||
    !attempt ||
    state.exp < now ||
    attempt.exp < now ||
    state.customer !== expectedCustomer ||
    attempt.customer !== expectedCustomer ||
    state.nonce !== attempt.nonce ||
    !attempt.verifier
  ) {
    return null;
  }
  return attempt;
}

export async function exchangeSalesforceCode(
  code: string,
  verifier: string,
  requestUrl: string,
): Promise<SalesforceTokenResponse> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    client_id: salesforceClientId(),
    client_secret: salesforceClientSecret(),
    redirect_uri: salesforceRedirectUri(requestUrl),
    code_verifier: verifier,
  });
  const response = await fetch(
    new URL("/services/oauth2/token", salesforceLoginUrl()),
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`Salesforce token exchange failed (${response.status}).`);
  }
  const token = (await response.json()) as SalesforceTokenResponse;
  if (!token.access_token || !token.refresh_token || !token.instance_url) {
    throw new Error(
      "Salesforce did not return the access, refresh, and instance values required for a durable connection.",
    );
  }
  return token;
}

export function salesforceIdentity(token: SalesforceTokenResponse): {
  orgId: string;
  userId: string;
} {
  if (!token.id) return { orgId: "unknown", userId: "" };
  try {
    const parts = new URL(token.id).pathname.split("/").filter(Boolean);
    const idIndex = parts.lastIndexOf("id");
    if (idIndex >= 0 && parts.length >= idIndex + 3) {
      return { orgId: parts[idIndex + 1], userId: parts[idIndex + 2] };
    }
  } catch {
    // The identity URL is metadata only. Keep the connection usable if a
    // Salesforce-compatible test org omits or changes it.
  }
  return { orgId: "unknown", userId: "" };
}

export function salesforceOAuthCookieOptions() {
  return {
    httpOnly: true as const,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/api/salesforce/oauth",
    maxAge: SALESFORCE_OAUTH_MAX_AGE_SECONDS,
  };
}

export function salesforceOAuthConfigured(): boolean {
  return Boolean(
    process.env.SALESFORCE_CLIENT_ID?.trim() &&
      process.env.SALESFORCE_CLIENT_SECRET?.trim() &&
      (process.env.SALESFORCE_OAUTH_REDIRECT_URI?.trim() ||
        process.env.VERCEL_ENV !== "production") &&
      (process.env.SALESFORCE_TOKEN_ENCRYPTION_KEY?.trim() ||
        process.env.VERCEL_ENV !== "production") &&
      (process.env.DATABASE_URL?.trim() ||
        process.env.VERCEL_ENV !== "production"),
  );
}
