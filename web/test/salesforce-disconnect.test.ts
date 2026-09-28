import { beforeEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 5: disconnectSalesforce used to swallow both
// a decrypt failure (thrown straight out, never reaching deleteConnection)
// and a failed/unconfirmed revoke (caught with a bare comment, nothing
// reported), so the UI always said "tokens removed" even when the refresh
// token was still live at Salesforce, or the local row never got cleaned up
// at all when the stored tokens could not be decrypted.

const connection = {
  customer_ref: "tenant-a",
  org_id: "org",
  user_id: "user",
  instance_url: "https://tenant.my.salesforce.com",
  access_token: "access",
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
};

const store = vi.hoisted(() => ({
  getSalesforceConnection: vi.fn(async () => connection),
  deleteSalesforceConnection: vi.fn(async () => undefined),
}));

vi.mock("@/lib/salesforce-store", () => store);
vi.mock("@/lib/salesforce-oauth", () => ({
  salesforceLoginUrl: () => "https://login.salesforce.com",
}));

import { disconnectSalesforce } from "@/lib/salesforce-client";
import { SalesforceTokenDecryptionError } from "@/lib/salesforce-crypto";

describe("disconnectSalesforce", () => {
  beforeEach(() => {
    store.getSalesforceConnection.mockClear();
    store.deleteSalesforceConnection.mockClear();
    store.getSalesforceConnection.mockImplementation(async () => connection);
  });

  it("reports revocationConfirmed: true when Salesforce accepts the revoke", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 200 })));
    const result = await disconnectSalesforce("tenant-a");
    expect(result).toEqual({ revocationConfirmed: true });
    expect(store.deleteSalesforceConnection).toHaveBeenCalledWith("tenant-a");
    vi.unstubAllGlobals();
  });

  it("reports revocationConfirmed: false and logs a cause code when Salesforce rejects the revoke", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 400 })));
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const result = await disconnectSalesforce("tenant-a");
    expect(result).toEqual({ revocationConfirmed: false });
    expect(store.deleteSalesforceConnection).toHaveBeenCalledWith("tenant-a");
    expect(error).toHaveBeenCalledWith(expect.stringContaining("rejected the revoke"));
    error.mockRestore();
    vi.unstubAllGlobals();
  });

  it("reports revocationConfirmed: false and logs a cause code on a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("ECONNRESET"); }));
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const result = await disconnectSalesforce("tenant-a");
    expect(result).toEqual({ revocationConfirmed: false });
    expect(error).toHaveBeenCalledWith(
      expect.stringContaining("network/timeout"),
      expect.any(Error),
    );
    error.mockRestore();
    vi.unstubAllGlobals();
  });

  it("still deletes the local row and reports confirmed when the stored tokens cannot be decrypted", async () => {
    store.getSalesforceConnection.mockImplementation(async () => {
      throw new SalesforceTokenDecryptionError(new Error("bad tag"));
    });
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await disconnectSalesforce("tenant-a");

    expect(result).toEqual({ revocationConfirmed: true });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(store.deleteSalesforceConnection).toHaveBeenCalledWith("tenant-a");
    expect(error).toHaveBeenCalledWith(
      expect.stringContaining("could not decrypt stored tokens"),
      expect.any(SalesforceTokenDecryptionError),
    );
    error.mockRestore();
    vi.unstubAllGlobals();
  });
});
