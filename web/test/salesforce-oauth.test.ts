import { createHash } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createSalesforceOAuthAttempt,
  verifySalesforceOAuthAttempt,
} from "@/lib/salesforce-oauth";

describe("Salesforce OAuth attempt", () => {
  beforeEach(() => {
    vi.stubEnv("PRICEKEEL_SECRET", "test-pricekeel-secret");
    vi.stubEnv("SALESFORCE_CLIENT_ID", "test-client-id");
    vi.stubEnv("SALESFORCE_CLIENT_SECRET", "test-client-secret");
    vi.stubEnv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com");
    vi.stubEnv(
      "SALESFORCE_OAUTH_REDIRECT_URI",
      "https://www.pricekeel.com/api/salesforce/oauth/callback",
    );
  });

  it("binds state to the tenant and sends a valid S256 PKCE challenge", () => {
    const attempt = createSalesforceOAuthAttempt(
      "tenant-a",
      "https://www.pricekeel.com/api/salesforce/oauth/start",
    );
    const authorization = new URL(attempt.authorizationUrl);
    const state = authorization.searchParams.get("state") ?? "";
    const verified = verifySalesforceOAuthAttempt(
      state,
      attempt.cookieValue,
      "tenant-a",
    );

    expect(verified).not.toBeNull();
    expect(authorization.searchParams.get("code_challenge_method")).toBe("S256");
    expect(authorization.searchParams.get("scope")).toBe("api refresh_token");
    expect(authorization.searchParams.get("code_challenge")).toBe(
      createHash("sha256").update(verified!.verifier).digest("base64url"),
    );
    expect(
      verifySalesforceOAuthAttempt(state, attempt.cookieValue, "tenant-b"),
    ).toBeNull();
  });

  it("rejects a tampered state value", () => {
    const attempt = createSalesforceOAuthAttempt(
      "tenant-a",
      "https://www.pricekeel.com/api/salesforce/oauth/start",
    );
    const authorization = new URL(attempt.authorizationUrl);
    const state = authorization.searchParams.get("state") ?? "";
    const tampered = `${state.slice(0, -1)}${state.endsWith("a") ? "b" : "a"}`;

    expect(
      verifySalesforceOAuthAttempt(tampered, attempt.cookieValue, "tenant-a"),
    ).toBeNull();
  });
});
