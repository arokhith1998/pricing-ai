import { describe, expect, it } from "vitest";

import { assessReadiness, type CanonicalCrmDeal } from "@/lib/salesforce-adapter";
import { DEFAULT_SALESFORCE_MAPPING } from "@/lib/salesforce-store";

function deal(overrides: Partial<CanonicalCrmDeal> = {}): CanonicalCrmDeal {
  return {
    opportunity_id: "SF-1",
    account_id: "",
    account_name: "Acme",
    outcome: "closed_won",
    created_date: "2026-01-01",
    close_date: "2026-02-01",
    segment: "MidMarket",
    industry: "",
    product_tier: "",
    value_metric: "seats",
    list_acv: 100_000,
    booked_acv: 80_000,
    quantity: null,
    term_months: null,
    rep_id: "",
    approved_by: "",
    competitor_present: false,
    currency_iso: "USD",
    salesforce_url: "",
    ...overrides,
  };
}

const UNMAPPED = DEFAULT_SALESFORCE_MAPPING; // list_value_field is ""
const MAPPED = {
  ...DEFAULT_SALESFORCE_MAPPING,
  mapping: { ...DEFAULT_SALESFORCE_MAPPING.mapping, list_value_field: "List_ACV__c" },
};

function closedBook(n: number, make: (i: number) => Partial<CanonicalCrmDeal>): CanonicalCrmDeal[] {
  return Array.from({ length: n }, (_, i) => deal({ opportunity_id: `SF-${i}`, ...make(i) }));
}

describe("assessReadiness list-value integrity (Gap 3)", () => {
  it("blocks a degenerate book where list equals booked, with an unmapped list field", () => {
    const records = closedBook(40, (i) => ({ list_acv: 90_000 + i, booked_acv: 90_000 + i }));
    const r = assessReadiness(records, UNMAPPED);
    expect(r.list_source).toBe("line_items");
    expect(r.blockers.some((b) => /no discount|booked amount/i.test(b))).toBe(true);
  });

  it("does not block an honest low-discount book when the list field is explicitly mapped", () => {
    // Same zero-discount shape, but a real list field is mapped: trust it.
    const records = closedBook(40, (i) => ({ list_acv: 90_000 + i, booked_acv: 90_000 + i }));
    const r = assessReadiness(records, MAPPED);
    expect(r.list_source).toBe("mapped_field");
    expect(r.blockers.some((b) => /discount|booked amount|list value/i.test(b))).toBe(false);
  });

  it("does not block a healthy book with real discount spread", () => {
    const records = closedBook(40, (i) => ({ list_acv: 100_000, booked_acv: 70_000 + i * 100 }));
    const r = assessReadiness(records, UNMAPPED);
    expect(r.closed_usable).toBe(40);
    expect(r.blockers.some((b) => /discount|list value/i.test(b))).toBe(false);
  });

  it("blocks when a large share of opportunities have no usable list value and no field is mapped", () => {
    const usable = closedBook(40, () => ({ list_acv: 100_000, booked_acv: 75_000 }));
    const missing = closedBook(10, (i) => ({ opportunity_id: `SF-MISS-${i}`, list_acv: null }));
    const r = assessReadiness([...usable, ...missing], UNMAPPED);
    expect(r.missing_list_value).toBe(10);
    expect(r.blockers.some((b) => /no usable list value|no pre-discount list field/i.test(b))).toBe(true);
  });
});
