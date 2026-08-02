import { beforeEach, describe, expect, it, vi } from "vitest";

const store = vi.hoisted(() => ({
  connection: {
    customer_ref: "tenant-a",
    org_id: "org",
    user_id: "user",
    instance_url: "https://tenant.my.salesforce.com",
    access_token: "expired-access",
    refresh_token: "durable-refresh",
    token_type: "Bearer",
    scope: "api refresh_token",
    issued_at: "",
    status: "connected" as const,
    last_error: "",
    last_sync_at: null,
    last_sync_closed: 0,
    last_sync_open: 0,
    connected_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
  },
  update: vi.fn(),
  mark: vi.fn(),
}));

vi.mock("@/lib/salesforce-store", () => ({
  deleteSalesforceConnection: vi.fn(),
  getSalesforceConnection: vi.fn(async () => store.connection),
  markSalesforceConnection: store.mark,
  updateSalesforceTokens: vi.fn(async (_customer: string, input: { access_token: string }) => {
    store.connection = { ...store.connection, access_token: input.access_token };
    store.update(input);
  }),
}));

vi.mock("@/lib/salesforce-oauth", () => ({
  salesforceLoginUrl: () => "https://login.salesforce.com",
}));

import { querySalesforce } from "@/lib/salesforce-client";

describe("Salesforce API refresh", () => {
  beforeEach(() => {
    vi.stubEnv("SALESFORCE_CLIENT_ID", "test-client-id");
    vi.stubEnv("SALESFORCE_CLIENT_SECRET", "test-client-secret");
    store.connection = {
      ...store.connection,
      access_token: "expired-access",
      refresh_token: "durable-refresh",
      status: "connected",
    };
    store.update.mockClear();
    store.mark.mockClear();
  });

  it("refreshes once after 401 and preserves the existing refresh token", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("", { status: 401 }))
      .mockResolvedValueOnce(Response.json({
        access_token: "rotated-access",
        instance_url: "https://tenant.my.salesforce.com",
      }))
      .mockResolvedValueOnce(Response.json({
        totalSize: 1,
        done: true,
        records: [{ Id: "006-test" }],
      }));
    vi.stubGlobal("fetch", fetchMock);

    const rows = await querySalesforce<{ Id: string }>(
      "tenant-a",
      "SELECT Id FROM Opportunity",
    );

    expect(rows).toEqual([{ Id: "006-test" }]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(store.update).toHaveBeenCalledWith(expect.objectContaining({
      access_token: "rotated-access",
      refresh_token: undefined,
    }));
    expect(store.connection.refresh_token).toBe("durable-refresh");
  });

  it("marks a second 401 as requiring reauthorization", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response("", { status: 401 }))
      .mockResolvedValueOnce(Response.json({ access_token: "rotated-access" }))
      .mockResolvedValueOnce(new Response("", { status: 401 })));

    await expect(
      querySalesforce("tenant-a", "SELECT Id FROM Opportunity"),
    ).rejects.toThrow("Reconnect the org");
    expect(store.mark).toHaveBeenCalledWith(
      "tenant-a",
      "reauth_required",
      expect.stringContaining("401"),
    );
  });
});
