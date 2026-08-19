import { beforeEach, describe, expect, it, vi } from "vitest";

import { hubspotTarget } from "@/lib/hubspot-client";
import {
  createHubspotOAuthAttempt,
  hubspotExpiryIso,
  hubspotOAuthConfigured,
  HUBSPOT_SCOPES,
  verifyHubspotOAuthAttempt,
} from "@/lib/hubspot-oauth";

const START_URL = "https://www.pricekeel.com/api/hubspot/oauth/start";

describe("HubSpot OAuth attempt", () => {
  beforeEach(() => {
    vi.stubEnv("PRICEKEEL_SECRET", "test-pricekeel-secret");
    vi.stubEnv("HUBSPOT_CLIENT_ID", "test-client-id");
    vi.stubEnv("HUBSPOT_CLIENT_SECRET", "test-client-secret");
    vi.stubEnv(
      "HUBSPOT_OAUTH_REDIRECT_URI",
      "https://www.pricekeel.com/api/hubspot/oauth/callback",
    );
  });

  it("binds state to the tenant and requests only read scopes", () => {
    const attempt = createHubspotOAuthAttempt("tenant-a", START_URL);
    const authorization = new URL(attempt.authorizationUrl);
    const state = authorization.searchParams.get("state") ?? "";

    expect(authorization.origin + authorization.pathname).toBe(
      "https://app.hubspot.com/oauth/authorize",
    );
    expect(
      verifyHubspotOAuthAttempt(state, attempt.cookieValue, "tenant-a"),
    ).not.toBeNull();

    const scopes = (authorization.searchParams.get("scope") ?? "").split(" ");
    expect(scopes).toEqual([...HUBSPOT_SCOPES]);
    // Slice 2 connects and reads. A write scope slipping in would silently
    // widen what a customer is consenting to at the install dialog.
    expect(scopes.some((scope) => scope.endsWith(".write"))).toBe(false);
  });

  it("sends no PKCE parameters, because HubSpot does not support them", () => {
    const authorization = new URL(
      createHubspotOAuthAttempt("tenant-a", START_URL).authorizationUrl,
    );
    expect(authorization.searchParams.get("code_challenge")).toBeNull();
    expect(authorization.searchParams.get("code_challenge_method")).toBeNull();
  });

  it("rejects a state issued for a different tenant", () => {
    const attempt = createHubspotOAuthAttempt("tenant-a", START_URL);
    const state =
      new URL(attempt.authorizationUrl).searchParams.get("state") ?? "";
    expect(
      verifyHubspotOAuthAttempt(state, attempt.cookieValue, "tenant-b"),
    ).toBeNull();
  });

  it("rejects a state whose nonce does not match the cookie", () => {
    const first = createHubspotOAuthAttempt("tenant-a", START_URL);
    const second = createHubspotOAuthAttempt("tenant-a", START_URL);
    const stateFromFirst =
      new URL(first.authorizationUrl).searchParams.get("state") ?? "";
    // Same tenant, valid signatures on both, but they belong to different
    // authorization attempts. Nonce pairing is the CSRF defence standing in
    // for the PKCE verifier.
    expect(
      verifyHubspotOAuthAttempt(stateFromFirst, second.cookieValue, "tenant-a"),
    ).toBeNull();
  });

  it("rejects a tampered state", () => {
    const attempt = createHubspotOAuthAttempt("tenant-a", START_URL);
    const state =
      new URL(attempt.authorizationUrl).searchParams.get("state") ?? "";
    const [payload] = state.split(".");
    expect(
      verifyHubspotOAuthAttempt(
        `${payload}.not-a-valid-signature`,
        attempt.cookieValue,
        "tenant-a",
      ),
    ).toBeNull();
  });

  it("rejects an expired attempt", () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-08-18T12:00:00Z"));
      const attempt = createHubspotOAuthAttempt("tenant-a", START_URL);
      const state =
        new URL(attempt.authorizationUrl).searchParams.get("state") ?? "";
      expect(
        verifyHubspotOAuthAttempt(state, attempt.cookieValue, "tenant-a"),
      ).not.toBeNull();

      vi.setSystemTime(new Date("2026-08-18T12:11:00Z"));
      expect(
        verifyHubspotOAuthAttempt(state, attempt.cookieValue, "tenant-a"),
      ).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("HubSpot token expiry", () => {
  it("uses expires_in when present and falls back to 30 minutes", () => {
    vi.useFakeTimers();
    try {
      const now = new Date("2026-08-18T12:00:00Z");
      vi.setSystemTime(now);
      expect(hubspotExpiryIso({ access_token: "t", expires_in: 600 })).toBe(
        new Date(now.getTime() + 600_000).toISOString(),
      );
      // A missing or nonsensical expires_in must not produce a token that
      // looks permanently valid.
      expect(hubspotExpiryIso({ access_token: "t" })).toBe(
        new Date(now.getTime() + 1_800_000).toISOString(),
      );
      expect(hubspotExpiryIso({ access_token: "t", expires_in: -5 })).toBe(
        new Date(now.getTime() + 1_800_000).toISOString(),
      );
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("HubSpot API path guard", () => {
  it("allows CRM and OAuth paths on the HubSpot host", () => {
    expect(hubspotTarget("/crm/v3/objects/deals").toString()).toBe(
      "https://api.hubapi.com/crm/v3/objects/deals",
    );
    expect(hubspotTarget("/crm/v3/pipelines/deals").toString()).toBe(
      "https://api.hubapi.com/crm/v3/pipelines/deals",
    );
  });

  it("blocks other hosts and unlisted paths", () => {
    expect(() => hubspotTarget("https://evil.example.com/crm/v3/objects/deals"))
      .toThrow(/invalid HubSpot API URL/);
    expect(() => hubspotTarget("/settings/v3/users")).toThrow(
      /invalid HubSpot API URL/,
    );
    // A relative traversal must not escape the allowed prefixes.
    expect(() => hubspotTarget("/crm/../settings/v3/users")).toThrow(
      /invalid HubSpot API URL/,
    );
  });
});

describe("HubSpot OAuth configuration check", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.stubEnv("VERCEL_ENV", "production");
    vi.stubEnv("HUBSPOT_CLIENT_ID", "id");
    vi.stubEnv("HUBSPOT_CLIENT_SECRET", "secret");
    vi.stubEnv(
      "HUBSPOT_OAUTH_REDIRECT_URI",
      "https://www.pricekeel.com/api/hubspot/oauth/callback",
    );
    vi.stubEnv("DATABASE_URL", "postgres://example");
  });

  it("accepts either the new or the legacy token encryption key name", () => {
    vi.stubEnv("CRM_TOKEN_ENCRYPTION_KEY", "");
    vi.stubEnv("SALESFORCE_TOKEN_ENCRYPTION_KEY", "");
    expect(hubspotOAuthConfigured()).toBe(false);

    vi.stubEnv("SALESFORCE_TOKEN_ENCRYPTION_KEY", "legacy-key");
    expect(hubspotOAuthConfigured()).toBe(true);

    vi.stubEnv("SALESFORCE_TOKEN_ENCRYPTION_KEY", "");
    vi.stubEnv("CRM_TOKEN_ENCRYPTION_KEY", "new-key");
    expect(hubspotOAuthConfigured()).toBe(true);
  });
});
