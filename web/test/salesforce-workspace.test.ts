import { beforeEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 3: a thin book (readiness passes the naive
// 30-closed-deal floor) whose engine-side per-band reference is still
// insufficient used to bubble a 422 straight out of loadSalesforceWorkspace,
// which workspace/route.ts's catch-all then read as "needs reauthorization".
// This exercises the real loadSalesforceWorkspace() against a stubbed
// /crm/analyze 422, mocking only the Salesforce adapter/store module
// boundary, following the pattern in salesforce-client.test.ts.

const DEFAULT_MAPPING = {
  mapping: {
    list_value_field: "",
    booked_value_field: "Amount",
    segment_field: "",
    product_field: "",
    value_metric_field: "",
    competitor_field: "",
    approved_by_field: "",
    term_months_field: "",
  },
  policy_threshold_pct: 15,
  default_value_metric: "hybrid" as const,
};

const markSalesforceSync = vi.hoisted(() => vi.fn(async () => undefined));
const getSalesforceMapping = vi.hoisted(() => vi.fn(async () => DEFAULT_MAPPING));

vi.mock("@/lib/salesforce-store", () => ({
  markSalesforceSync,
  getSalesforceMapping,
}));

const OPEN_DEAL_RECORD = {
  opportunity_id: "006-open-1",
  account_id: "001",
  account_name: "Thin Book Co",
  outcome: "open" as const,
  created_date: "2026-01-01",
  close_date: "2026-10-01",
  segment: "Enterprise",
  industry: "",
  product_tier: "",
  value_metric: "hybrid" as const,
  list_acv: 200_000,
  booked_acv: 180_000,
  quantity: null,
  term_months: null,
  rep_id: "",
  approved_by: "",
  competitor_present: false,
  currency_iso: "USD",
  salesforce_url: "",
};

vi.mock("@/lib/salesforce-adapter", () => ({
  fetchSalesforceCanonicalDeals: vi.fn(async () => ({
    records: [OPEN_DEAL_RECORD],
    fields: [],
    readiness: {
      records_fetched: 1,
      closed_usable: 0,
      open_usable: 1,
      missing_list_value: 0,
      missing_booked_value: 0,
      currencies: ["USD"],
      list_source: "line_items" as const,
      blockers: [],
      warnings: [],
    },
  })),
}));

import { loadSalesforceWorkspace } from "@/lib/salesforce-workspace";

const INSUFFICIENT_MESSAGE =
  "Insufficient closed-deal data for a defensible reference discount (segment 'Enterprise'): " +
  "no 3 real discount bands each clear 15 closed deals. Band counts: 0-5%=12. Collect more " +
  "closed Salesforce opportunities before quoting a guardrail on this deal.";

describe("loadSalesforceWorkspace: engine data refusal vs. connection failure", () => {
  beforeEach(() => {
    markSalesforceSync.mockClear();
    getSalesforceMapping.mockClear();
  });

  it("turns a 422 from /crm/analyze into a readiness blocker, not a thrown error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        expect(String(url)).toContain("/crm/analyze");
        return Response.json({ detail: INSUFFICIENT_MESSAGE }, { status: 422 });
      }),
    );

    const workspace = await loadSalesforceWorkspace("tenant-a");

    expect(workspace.analysis).toBeNull();
    expect(workspace.guidance).toEqual([]);
    expect(workspace.source_readiness.blockers).toContainEqual(
      expect.stringContaining("Insufficient closed-deal data"),
    );
    expect(workspace.source_readiness.blockers).toContainEqual(
      expect.stringContaining("Band counts"),
    );
    // A data refusal still counts as a completed sync of the connection.
    expect(markSalesforceSync).toHaveBeenCalledWith("tenant-a", 0, 1);

    vi.unstubAllGlobals();
  });

  it("still throws (so workspace/route.ts can classify it as a connection problem) on a 5xx from /crm/analyze", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ detail: "engine crashed" }, { status: 500 })),
    );

    await expect(loadSalesforceWorkspace("tenant-a")).rejects.toThrow();

    vi.unstubAllGlobals();
  });
});
