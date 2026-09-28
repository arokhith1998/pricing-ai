import { beforeEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 3, second half: workspace/route.ts's catch-all
// must reserve `degraded` (the "Reconnect Salesforce" UI) for a connection
// whose own status says it needs reauthorization, not for every error that
// happens to reach it while a connection row still exists. A data-readiness
// refusal is caught and reshaped inside loadSalesforceWorkspace() (see
// salesforce-workspace.test.ts); anything that still throws past that point
// is either a real connection problem or an unrelated outage, and this test
// exercises the route's classification of both.

vi.mock("@/lib/gate", () => ({
  requireAccess: vi.fn(async () => null),
  customerRef: vi.fn(async () => "tenant-a"),
}));

const connectionState = vi.hoisted(() => ({
  status: "connected" as "connected" | "reauth_required",
}));

vi.mock("@/lib/salesforce-store", () => ({
  getSalesforceConnection: vi.fn(async () => ({
    customer_ref: "tenant-a",
    org_id: "org",
    instance_url: "https://tenant.my.salesforce.com",
    status: connectionState.status,
    last_error: "",
  })),
  publicSalesforceConnection: vi.fn((c: unknown) => c),
}));

vi.mock("@/lib/salesforce-workspace", () => ({
  loadSalesforceWorkspace: vi.fn(async () => {
    throw new Error("Salesforce sync failed.");
  }),
}));

import { GET } from "@/app/api/salesforce/workspace/route";

describe("GET /api/salesforce/workspace: degraded reserved for connection status", () => {
  beforeEach(() => {
    connectionState.status = "connected";
  });

  it("returns a plain 502 (not degraded) when the connection is still healthy but sync failed", async () => {
    connectionState.status = "connected";
    const res = await GET();
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.degraded).toBeUndefined();
    expect(body.error).toMatch(/salesforce sync failed/i);
  });

  it("returns a degraded 200 when the connection status itself flipped to reauth_required", async () => {
    connectionState.status = "reauth_required";
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.degraded).toBe(true);
    expect(body.connection.status).toBe("reauth_required");
  });
});
