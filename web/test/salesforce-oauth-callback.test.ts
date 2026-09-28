import { beforeEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 5: every failure in the OAuth callback
// (token exchange, origin validation, encryption-key misconfiguration,
// DATABASE_URL misconfiguration, or a real save failure) used to fold into
// the same unlogged "token_exchange_failed" redirect. This checks that each
// path now logs a distinguishable cause code server-side; the user-facing
// redirect is intentionally unchanged (still generic, so it never leaks
// which internal precondition failed).

const cookieStore = vi.hoisted(() => ({ get: () => ({ value: "attempt-cookie" }), set: vi.fn() }));
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => cookieStore) }));
vi.mock("@/lib/gate", () => ({ customerRef: vi.fn(async () => "tenant-a") }));
vi.mock("@/lib/salesforce-client", () => ({
  validatedSalesforceOrigin: vi.fn((raw: string) => new URL(raw).origin),
}));

const oauth = vi.hoisted(() => ({
  verifySalesforceOAuthAttempt: vi.fn(() => ({ customer: "tenant-a", verifier: "v" })),
  exchangeSalesforceCode: vi.fn(async () => ({
    access_token: "at",
    refresh_token: "rt",
    instance_url: "https://tenant.my.salesforce.com",
    id: "https://login.salesforce.com/id/00Dxx/005xx",
    token_type: "Bearer",
    issued_at: "",
    scope: "api refresh_token",
  })),
  salesforceIdentity: vi.fn(() => ({ orgId: "00Dxx", userId: "005xx" })),
  SALESFORCE_OAUTH_COOKIE: "pk_sf_oauth",
  salesforceOAuthCookieOptions: vi.fn(() => ({})),
}));
vi.mock("@/lib/salesforce-oauth", () => oauth);

const saveSalesforceConnection = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock("@/lib/salesforce-store", () => ({ saveSalesforceConnection }));

import { GET } from "@/app/api/salesforce/oauth/callback/route";

function req() {
  return new Request(
    "https://pricekeel.com/api/salesforce/oauth/callback?code=abc&state=xyz",
  );
}

describe("GET /api/salesforce/oauth/callback: cause-code logging", () => {
  let error: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    error = vi.spyOn(console, "error").mockImplementation(() => {});
    saveSalesforceConnection.mockClear();
    saveSalesforceConnection.mockImplementation(async () => undefined);
  });

  it("logs cause=exchange when the token exchange itself fails", async () => {
    oauth.exchangeSalesforceCode.mockRejectedValueOnce(new Error("Salesforce token endpoint 400"));
    const res = await GET(req());
    expect(res.headers.get("location")).toContain("error=token_exchange_failed");
    expect(error).toHaveBeenCalledWith(expect.stringContaining("cause=exchange"), expect.any(Error));
  });

  it("logs cause=key when SALESFORCE_TOKEN_ENCRYPTION_KEY is missing/misconfigured", async () => {
    saveSalesforceConnection.mockRejectedValueOnce(
      new Error("SALESFORCE_TOKEN_ENCRYPTION_KEY is required in production."),
    );
    const res = await GET(req());
    expect(res.headers.get("location")).toContain("error=token_exchange_failed");
    expect(error).toHaveBeenCalledWith(expect.stringContaining("cause=key"), expect.any(Error));
  });

  it("logs cause=database_url when DATABASE_URL is missing/unreachable", async () => {
    saveSalesforceConnection.mockRejectedValueOnce(
      new Error("DATABASE_URL is required for durable Salesforce connections."),
    );
    const res = await GET(req());
    expect(res.headers.get("location")).toContain("error=token_exchange_failed");
    expect(error).toHaveBeenCalledWith(expect.stringContaining("cause=database_url"), expect.any(Error));
  });

  it("logs cause=save_connection for any other save failure", async () => {
    saveSalesforceConnection.mockRejectedValueOnce(new Error("Neon: connection terminated"));
    const res = await GET(req());
    expect(res.headers.get("location")).toContain("error=token_exchange_failed");
    expect(error).toHaveBeenCalledWith(
      expect.stringContaining("cause=save_connection"),
      expect.any(Error),
    );
  });
});
