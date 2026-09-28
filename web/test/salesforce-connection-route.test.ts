import { beforeEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 5: a rotated SALESFORCE_TOKEN_ENCRYPTION_KEY
// used to surface as a 503 wrapping WebCrypto's opaque DOMException text;
// and DELETE always said "tokens removed" even when Salesforce never
// confirmed the revoke.

vi.mock("@/lib/gate", () => ({
  requireAccess: vi.fn(async () => null),
  customerRef: vi.fn(async () => "tenant-a"),
}));

vi.mock("@/lib/salesforce-oauth", () => ({
  salesforceOAuthConfigured: vi.fn(() => true),
}));

const state = vi.hoisted(() => ({
  getConnectionImpl: async () => null as unknown,
  disconnectImpl: async () => ({ revocationConfirmed: true }),
}));

vi.mock("@/lib/salesforce-store", () => ({
  getSalesforceConnection: vi.fn(() => state.getConnectionImpl()),
  publicSalesforceConnection: vi.fn((c: unknown) => c),
}));

vi.mock("@/lib/salesforce-client", () => ({
  disconnectSalesforce: vi.fn(() => state.disconnectImpl()),
}));

import { SalesforceTokenDecryptionError } from "@/lib/salesforce-crypto";
import { DELETE, GET } from "@/app/api/salesforce/connection/route";

describe("GET /api/salesforce/connection: decryption failure", () => {
  beforeEach(() => {
    state.getConnectionImpl = async () => null;
  });

  it("answers a rotated encryption key with a clear 409, not a 503", async () => {
    state.getConnectionImpl = async () => {
      throw new SalesforceTokenDecryptionError(new Error("bad tag"));
    };
    const res = await GET();
    expect(res.status).toBe(409);
    const body = await res.json();
    expect(body.error).toMatch(/could not be decrypted/i);
    expect(body.error).not.toMatch(/operation-specific reason/i);
  });

  it("keeps the generic 503 for any other read failure", async () => {
    state.getConnectionImpl = async () => {
      throw new Error("Neon unreachable");
    };
    const res = await GET();
    expect(res.status).toBe(503);
  });
});

describe("DELETE /api/salesforce/connection: revocation_unconfirmed", () => {
  it("reports revocation_unconfirmed: false when Salesforce confirmed the revoke", async () => {
    state.disconnectImpl = async () => ({ revocationConfirmed: true });
    const res = await DELETE();
    const body = await res.json();
    expect(body).toEqual({ disconnected: true, revocation_unconfirmed: false });
  });

  it("reports revocation_unconfirmed: true when Salesforce did not confirm the revoke", async () => {
    state.disconnectImpl = async () => ({ revocationConfirmed: false });
    const res = await DELETE();
    const body = await res.json();
    expect(body).toEqual({ disconnected: true, revocation_unconfirmed: true });
  });
});
