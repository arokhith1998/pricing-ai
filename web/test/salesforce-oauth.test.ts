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
    const [payload, signature] = state.split(".");

    // Tamper the FIRST character of a segment, never the last. base64url packs
    // the 32-byte HMAC into 43 characters, so the final character carries only
    // 4 significant bits and four different characters decode to identical
    // bytes. Swapping it leaves the signature byte-for-byte unchanged about one
    // time in sixteen, verification correctly succeeds, and the test would fail
    // as if signature checking were broken. The first character of any segment
    // contributes all six of its bits, so changing it always changes the bytes.
    const swapFirst = (segment: string) =>
      `${segment[0] === "A" ? "B" : "A"}${segment.slice(1)}`;

    expect(
      verifySalesforceOAuthAttempt(
        `${swapFirst(payload)}.${signature}`,
        attempt.cookieValue,
        "tenant-a",
      ),
    ).toBeNull();
    expect(
      verifySalesforceOAuthAttempt(
        `${payload}.${swapFirst(signature)}`,
        attempt.cookieValue,
        "tenant-a",
      ),
    ).toBeNull();
  });
});
