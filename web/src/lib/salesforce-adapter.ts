import "server-only";

import {
  describeSalesforceOpportunity,
  querySalesforce,
  type SalesforceDescribeField,
} from "@/lib/salesforce-client";
import type { SalesforceMappingConfig } from "@/lib/salesforce-store";

const API_FIELD = /^[A-Za-z][A-Za-z0-9_]*$/;
const LOOKBACK_DAYS = 730;

type SalesforceRecord = Record<string, unknown> & {
  OpportunityLineItems?: { records?: Array<Record<string, unknown>> };
};

// Mirrors pricing/schema.py SourceSystem and CostBasis (PK-23, ADR-006).
export const SOURCE_SYSTEMS = [
  "csv",
  "salesforce",
  "hubspot",
  "cpq",
  "billing",
  "manual",
] as const;
export type SourceSystem = (typeof SOURCE_SYSTEMS)[number];
export type CostBasis = "crm_proxy" | "declared_cost" | "erp_verified";

export type CanonicalDeal = {
  opportunity_id: string;
  account_id: string;
  account_name: string;
  outcome: "closed_won" | "closed_lost" | "open";
  created_date: string;
  close_date: string;
  segment: string;
  industry: string;
  product_tier: string;
  value_metric: "seats" | "consumption" | "hybrid";
  list_acv: number | null;
  booked_acv: number | null;
  quantity: number | null;
  term_months: number | null;
  rep_id: string;
  approved_by: string;
  competitor_present: boolean;
  currency_iso: string;
  salesforce_url: string;
  // Provenance and contract-structure fields (PK-23 / PK-26). All optional,
  // mirroring pricing/schema.py. Money fields are numbers in currency_iso.
  source_system?: SourceSystem;
  source_record_id?: string;
  source_account_id?: string;
  source_quote_id?: string;
  source_url?: string;
  value_metric_unit?: string;
  cost_basis?: CostBasis;
  list_unit_rate?: number;
  credits_tcv?: number;
};

/** @deprecated Renamed to CanonicalDeal in PK-26. Alias kept for one release. */
export type CanonicalCrmDeal = CanonicalDeal;

export type SalesforceReadiness = {
  records_fetched: number;
  closed_usable: number;
  open_usable: number;
  missing_list_value: number;
  missing_booked_value: number;
  currencies: string[];
  // How the list (pre-discount) value was resolved across the book. "none" and
  // an unmapped "line_items" fallback are where the silent-zero-discount risk
  // lives (Gap 3), so onboarding surfaces this.
  list_source: "mapped_field" | "line_items" | "none";
  blockers: string[];
  warnings: string[];
};

// Gap 3 thresholds. When no pre-discount list field is mapped, a book that is
// mostly missing-list or collapses to ~0 discount is a mapping error, not a
// real result. These fire a blocker, never a silent zero. They are gated on an
// unmapped list field so a disciplined seller with a real mapped list field and
// genuinely low discounts is never over-blocked.
const MISSING_LIST_BLOCK_SHARE = 0.2;
const DEGENERATE_LIST_SHARE = 0.9;
const ZERO_DISCOUNT_EPS = 0.0005;
// Ramp / annualization disclosure. The diagnostic treats booked value as
// annualized ACV, but Salesforce Amount is often total-contract or year-1 ramp
// value on multiyear deals. We cannot infer an org's convention, so we do not
// silently transform: we disclose when a material share of the book is
// multiyear so a misstated discount is caught, not hidden.
const MULTIYEAR_TERM_MONTHS = 24;
const MULTIYEAR_DISCLOSE_SHARE = 0.1;

function asText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const normalized = asText(value).replace(/[$,\s]/g, "");
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function asBoolean(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  return ["true", "yes", "1", "y"].includes(asText(value).toLowerCase());
}

function relationValue(record: SalesforceRecord, relation: string, field: string): string {
  const parent = record[relation];
  if (!parent || typeof parent !== "object") return "";
  return asText((parent as Record<string, unknown>)[field]);
}

function mappedValue(record: SalesforceRecord, field: string): unknown {
  return field ? record[field] : undefined;
}

function lineItems(record: SalesforceRecord): Array<Record<string, unknown>> {
  return record.OpportunityLineItems?.records ?? [];
}

function lineListValue(lines: Array<Record<string, unknown>>): number | null {
  if (!lines.length) return null;
  let total = 0;
  let usable = 0;
  for (const line of lines) {
    const price = asNumber(line.ListPrice);
    const quantity = asNumber(line.Quantity) ?? 1;
    if (price === null || quantity <= 0) continue;
    total += price * quantity;
    usable += 1;
  }
  return usable ? total : null;
}

function lineBookedValue(lines: Array<Record<string, unknown>>): number | null {
  if (!lines.length) return null;
  const values = lines.map((line) => asNumber(line.TotalPrice)).filter(
    (value): value is number => value !== null,
  );
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function lineQuantity(lines: Array<Record<string, unknown>>): number | null {
  const values = lines.map((line) => asNumber(line.Quantity)).filter(
    (value): value is number => value !== null,
  );
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function lineProduct(lines: Array<Record<string, unknown>>): string {
  for (const line of lines) {
    const pricebook = line.PricebookEntry;
    if (!pricebook || typeof pricebook !== "object") continue;
    const product = (pricebook as Record<string, unknown>).Product2;
    if (!product || typeof product !== "object") continue;
    const fields = product as Record<string, unknown>;
    const value = asText(fields.Family) || asText(fields.Name);
    if (value) return value;
  }
  return "";
}

function normalizeValueMetric(
  value: unknown,
  fallback: SalesforceMappingConfig["default_value_metric"],
): CanonicalDeal["value_metric"] {
  const text = asText(value).toLowerCase();
  if (text.includes("seat") || text.includes("user")) return "seats";
  if (text.includes("usage") || text.includes("consum")) return "consumption";
  if (text.includes("hybrid")) return "hybrid";
  return fallback;
}

function safeMappedFields(
  fields: SalesforceDescribeField[],
  config: SalesforceMappingConfig,
): string[] {
  const readable = new Set(fields.map((field) => field.name));
  return Object.values(config.mapping).filter(
    (name, index, all) =>
      Boolean(name) &&
      API_FIELD.test(name) &&
      readable.has(name) &&
      all.indexOf(name) === index,
  );
}

export function validateSalesforceMapping(
  fields: SalesforceDescribeField[],
  config: SalesforceMappingConfig,
): string[] {
  const readable = new Set(fields.map((field) => field.name));
  const errors: string[] = [];
  for (const [key, name] of Object.entries(config.mapping)) {
    if (!name) continue;
    if (!API_FIELD.test(name) || !readable.has(name)) {
      errors.push(`${key} references an unavailable Opportunity field.`);
    }
  }
  if (!(config.policy_threshold_pct >= 0 && config.policy_threshold_pct <= 40)) {
    errors.push("Policy threshold must be between 0 and 40 percent.");
  }
  if (!["seats", "consumption", "hybrid"].includes(config.default_value_metric)) {
    errors.push("Default value metric is invalid.");
  }
  return errors;
}

export async function fetchSalesforceCanonicalDeals(
  customerRef: string,
  config: SalesforceMappingConfig,
): Promise<{
  records: CanonicalDeal[];
  readiness: SalesforceReadiness;
  fields: SalesforceDescribeField[];
}> {
  const fields = await describeSalesforceOpportunity(customerRef);
  const mappingErrors = validateSalesforceMapping(fields, config);
  if (mappingErrors.length) throw new Error(mappingErrors.join(" "));
  const available = new Set(fields.map((field) => field.name));
  const selected = [
    "Id",
    "Name",
    "AccountId",
    "IsClosed",
    "IsWon",
    "StageName",
    "CreatedDate",
    "CloseDate",
    "Amount",
    "OwnerId",
    "Type",
  ].filter((name) => available.has(name));
  if (available.has("CurrencyIsoCode")) selected.push("CurrencyIsoCode");
  selected.push(...safeMappedFields(fields, config));
  selected.push("Account.Name", "Account.Type", "Account.Industry", "Owner.Name");
  selected.push(
    "(SELECT Quantity,ListPrice,TotalPrice,PricebookEntry.Product2.Family,PricebookEntry.Product2.Name FROM OpportunityLineItems)",
  );

  const unique = selected.filter((field, index) => selected.indexOf(field) === index);
  const soql = [
    `SELECT ${unique.join(",")}`,
    "FROM Opportunity",
    `WHERE (IsClosed = TRUE AND CloseDate = LAST_N_DAYS:${LOOKBACK_DAYS}) OR IsClosed = FALSE`,
    "ORDER BY IsClosed ASC, CloseDate DESC",
    "LIMIT 9999",
  ].join(" ");
  const raw = await querySalesforce<SalesforceRecord>(customerRef, soql);

  const records = raw.map((record): CanonicalDeal => {
    const lines = lineItems(record);
    const isClosed = asBoolean(record.IsClosed);
    const isWon = asBoolean(record.IsWon);
    const mappedList = asNumber(mappedValue(record, config.mapping.list_value_field));
    const mappedBooked = asNumber(
      mappedValue(record, config.mapping.booked_value_field),
    );
    const list = mappedList ?? lineListValue(lines);
    const booked = mappedBooked ?? asNumber(record.Amount) ?? lineBookedValue(lines);
    const opportunityId = asText(record.Id);
    const accountId = asText(record.AccountId);
    const recordUrl = `/lightning/r/Opportunity/${encodeURIComponent(opportunityId)}/view`;
    return {
      opportunity_id: opportunityId,
      account_id: accountId,
      account_name:
        relationValue(record, "Account", "Name") || asText(record.Name) || opportunityId,
      outcome: !isClosed ? "open" : isWon ? "closed_won" : "closed_lost",
      created_date: asText(record.CreatedDate).slice(0, 10),
      close_date: asText(record.CloseDate).slice(0, 10),
      segment:
        asText(mappedValue(record, config.mapping.segment_field)) ||
        relationValue(record, "Account", "Type") ||
        "Unknown",
      industry: relationValue(record, "Account", "Industry") || "Unknown",
      product_tier:
        asText(mappedValue(record, config.mapping.product_field)) ||
        lineProduct(lines) ||
        "Unknown",
      value_metric: normalizeValueMetric(
        mappedValue(record, config.mapping.value_metric_field),
        config.default_value_metric,
      ),
      list_acv: list,
      booked_acv: booked,
      quantity: lineQuantity(lines),
      term_months: asNumber(mappedValue(record, config.mapping.term_months_field)),
      rep_id: relationValue(record, "Owner", "Name") || asText(record.OwnerId),
      approved_by: asText(mappedValue(record, config.mapping.approved_by_field)),
      competitor_present: asBoolean(
        mappedValue(record, config.mapping.competitor_field),
      ),
      currency_iso: asText(record.CurrencyIsoCode),
      salesforce_url: recordUrl,
      source_system: "salesforce",
      source_record_id: opportunityId,
      ...(accountId ? { source_account_id: accountId } : {}),
      source_url: recordUrl,
    };
  });

  return { records, fields, readiness: assessReadiness(records, config) };
}

// Pure readiness assessment, split out from the network fetch so it is unit
// testable without a Salesforce round trip.
export function assessReadiness(
  records: CanonicalDeal[],
  config: SalesforceMappingConfig,
): SalesforceReadiness {
  const usable = (record: CanonicalDeal) =>
    record.list_acv !== null &&
    record.list_acv > 0 &&
    record.booked_acv !== null &&
    record.booked_acv >= 0;

  const closed = records.filter((record) => record.outcome !== "open");
  const open = records.filter((record) => record.outcome === "open");
  const missingList = records.filter(
    (record) => record.list_acv === null || record.list_acv <= 0,
  ).length;
  const missingBooked = records.filter(
    (record) => record.booked_acv === null || record.booked_acv < 0,
  ).length;
  const currencies = [...new Set(records.map((record) => record.currency_iso).filter(Boolean))];
  const closedUsable = closed.filter(usable);
  const openUsable = open.filter(usable).length;

  const listFieldMapped = Boolean(config.mapping.list_value_field);
  const hasAnyList = records.some((record) => record.list_acv !== null && record.list_acv > 0);
  const listSource: SalesforceReadiness["list_source"] = listFieldMapped
    ? "mapped_field"
    : hasAnyList
      ? "line_items"
      : "none";

  // Share of closed usable deals whose computed discount is ~0. When the list
  // value is really the booked amount, this collapses to nearly the whole book.
  const zeroDiscount = closedUsable.filter((record) => {
    const discount = 1 - (record.booked_acv as number) / (record.list_acv as number);
    return Math.abs(discount) <= ZERO_DISCOUNT_EPS;
  }).length;
  const zeroDiscountShare = closedUsable.length ? zeroDiscount / closedUsable.length : 0;
  const missingListShare = records.length ? missingList / records.length : 0;

  const blockers: string[] = [];
  const warnings: string[] = [];
  if (currencies.length > 1) {
    blockers.push(
      `Multiple Salesforce currencies are present (${currencies.join(", ")}); V1 will not combine them.`,
    );
  }
  // This 30-deal floor is a cheap, book-level pre-check, deliberately looser
  // than the pricing engine's actual requirement (metrics.SEGMENT_REF_MIN_
  // BANDS: 3 real discount bands each clearing 15 closed deals): 30 closed
  // deals bunched into one or two bands clears this floor but still cannot
  // support a reference discount. Silent-failure-hunter finding 3: passing
  // here used to read as "no blockers" right up until an open deal's
  // guidance call failed with a 422 that salesforce-workspace.ts's caller
  // then misclassified as a reauth/connection problem. Duplicating the
  // engine's exact per-band bucketing here would drift from pricing/
  // metrics.py, so the authoritative check instead stays server-side: a
  // CRMUpstreamError from /crm/analyze naming the actual band counts is
  // caught in salesforce-workspace.ts's loadSalesforceWorkspace() and
  // appended to this same `blockers` array, and workspace/route.ts reserves
  // `degraded` for a connection whose own status says so.
  if (closedUsable.length < 30) {
    blockers.push(
      `Only ${closedUsable.length} usable closed opportunities were found; at least 30 are required.`,
    );
  } else if (closedUsable.length < 500) {
    warnings.push(
      `${closedUsable.length} usable closed opportunities support a directional analysis; 500+ per year is the target for stable operating guidance.`,
    );
  }

  // Gap 3: an unmapped list field that resolves to booked, or a book that is
  // mostly missing list, blocks onboarding with a specific remedy. A mapped
  // list field is trusted, so honest low-discount books are never over-blocked.
  if (!listFieldMapped && closedUsable.length > 0 && zeroDiscountShare >= DEGENERATE_LIST_SHARE) {
    blockers.push(
      `List value resolves to the booked amount (${Math.round(zeroDiscountShare * 100)} percent of closed deals show no discount). Map a pre-discount Salesforce list field, or add Opportunity Products with true list prices, so discount and leakage are real.`,
    );
  } else if (!listFieldMapped && missingListShare >= MISSING_LIST_BLOCK_SHARE) {
    blockers.push(
      `No pre-discount list field is mapped and ${missingList} of ${records.length} opportunities have no usable list value. Map an annualized list field, or add Opportunity Products with true list prices.`,
    );
  } else if (missingList) {
    warnings.push(
      `${missingList} opportunities have no usable list value. Map an annualized list field or add Opportunity Products.`,
    );
  }
  if (missingBooked) {
    warnings.push(`${missingBooked} opportunities have no usable booked/quoted value.`);
  }

  // Ramp / annualization disclosure (live-CRM input boundary). Only counts deals
  // that actually carry a term, so an unmapped term field never fabricates the
  // signal.
  const multiyear = records.filter(
    (record) => record.term_months !== null && record.term_months >= MULTIYEAR_TERM_MONTHS,
  ).length;
  const multiyearShare = records.length ? multiyear / records.length : 0;
  if (multiyearShare >= MULTIYEAR_DISCLOSE_SHARE) {
    warnings.push(
      `${multiyear} opportunities run ${MULTIYEAR_TERM_MONTHS} months or longer. Pricekeel treats booked value as annualized ACV. If your booked field holds total-contract or year-1 ramp value, the discount on those deals is misstated. Confirm the booked field is annualized.`,
    );
  }

  return {
    records_fetched: records.length,
    closed_usable: closedUsable.length,
    open_usable: openUsable,
    missing_list_value: missingList,
    missing_booked_value: missingBooked,
    currencies,
    list_source: listSource,
    blockers,
    warnings,
  };
}
