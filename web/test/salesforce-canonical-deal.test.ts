import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/salesforce-client", () => ({
  describeSalesforceOpportunity: vi.fn(async () =>
    ["Id", "Name", "AccountId", "IsClosed", "IsWon", "CloseDate", "Amount"].map(
      (name) => ({ name, label: name, type: "string", custom: false }),
    ),
  ),
  querySalesforce: vi.fn(async () => [
    {
      Id: "006A",
      AccountId: "001B",
      Name: "Acme renewal",
      IsClosed: true,
      IsWon: true,
      CreatedDate: "2026-01-02T00:00:00.000+0000",
      CloseDate: "2026-03-04",
      Amount: 90000,
      OwnerId: "005C",
      Account: { Name: "Acme", Type: "Mid-Market", Industry: "Software" },
      Owner: { Name: "Rae Rep" },
      CurrencyIsoCode: "USD",
    },
    { Id: "006D", Name: "No account", IsClosed: false, IsWon: false, Amount: 100 },
  ]),
}));

import {
  assessReadiness,
  fetchSalesforceCanonicalDeals,
  SOURCE_SYSTEMS,
  type CanonicalCrmDeal,
  type CanonicalDeal,
} from "@/lib/salesforce-adapter";
import { DEFAULT_SALESFORCE_MAPPING } from "@/lib/salesforce-store";

const NEW_KEYS = ["source_system", "source_record_id", "source_account_id", "source_url"];

describe("CanonicalDeal adapter output (PK-26)", () => {
  it("keeps every pre-existing value unchanged and only adds provenance", async () => {
    const { records } = await fetchSalesforceCanonicalDeals(
      "tenant-a",
      DEFAULT_SALESFORCE_MAPPING,
    );
    const first: CanonicalDeal = records[0];
    const legacy: CanonicalCrmDeal = first;
    const old = Object.fromEntries(
      Object.entries(legacy).filter(([k]) => !NEW_KEYS.includes(k)),
    );
    expect(old).toEqual({
      opportunity_id: "006A",
      account_id: "001B",
      account_name: "Acme",
      outcome: "closed_won",
      created_date: "2026-01-02",
      close_date: "2026-03-04",
      segment: "Mid-Market",
      industry: "Software",
      product_tier: "Unknown",
      value_metric: "hybrid",
      list_acv: null,
      booked_acv: 90000,
      quantity: null,
      term_months: null,
      rep_id: "Rae Rep",
      approved_by: "",
      competitor_present: false,
      currency_iso: "USD",
      salesforce_url: "/lightning/r/Opportunity/006A/view",
    });
    expect(first.source_system).toBe("salesforce");
    expect(first.source_record_id).toBe("006A");
    expect(first.source_account_id).toBe("001B");
    expect(first.source_url).toBe(first.salesforce_url);
  });

  it("omits source_account_id when the Opportunity has no Account", async () => {
    const { records } = await fetchSalesforceCanonicalDeals(
      "tenant-a",
      DEFAULT_SALESFORCE_MAPPING,
    );
    expect("source_account_id" in records[1]).toBe(false);
    expect(records[1].source_record_id).toBe("006D");
  });

  it("readiness is unchanged by the provenance fields", async () => {
    const { records, readiness } = await fetchSalesforceCanonicalDeals(
      "tenant-a",
      DEFAULT_SALESFORCE_MAPPING,
    );
    const stripped = records.map((r) =>
      Object.fromEntries(
        Object.entries(r).filter(([k]) => !NEW_KEYS.includes(k)),
      ),
    ) as CanonicalDeal[];
    expect(readiness).toEqual(assessReadiness(stripped, DEFAULT_SALESFORCE_MAPPING));
    expect(readiness.records_fetched).toBe(2);
    expect(readiness.closed_usable).toBe(0);
    expect(readiness.open_usable).toBe(0);
  });

  it("source_url equals salesforce_url", async () => {
    const { records } = await fetchSalesforceCanonicalDeals(
      "tenant-a",
      DEFAULT_SALESFORCE_MAPPING,
    );
    for (const r of records) expect(r.source_url).toBe(r.salesforce_url);
  });
});

describe("SourceSystem parity with pricing/schema.py", () => {
  it("TypeScript union has exactly the Python enum members", () => {
    const text = readFileSync(resolve(process.cwd(), "../pricing/schema.py"), "utf-8");
    const block = text.match(/class SourceSystem\([^)]*\):([\s\S]*?)(?=\nclass |\n\S)/);
    expect(block).not.toBeNull();
    const members = [...block![1].matchAll(/^\s+[A-Z_]+\s*=\s*"([^"]+)"/gm)].map((m) => m[1]);
    expect(members.length).toBeGreaterThan(0);
    expect([...SOURCE_SYSTEMS].sort()).toEqual([...members].sort());
  });
});
