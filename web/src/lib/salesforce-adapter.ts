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

export type CanonicalCrmDeal = {
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
};

export type SalesforceReadiness = {
  records_fetched: number;
  closed_usable: number;
  open_usable: number;
  missing_list_value: number;
  missing_booked_value: number;
  currencies: string[];
  blockers: string[];
  warnings: string[];
};

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
): CanonicalCrmDeal["value_metric"] {
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
  records: CanonicalCrmDeal[];
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

  const records = raw.map((record): CanonicalCrmDeal => {
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
    return {
      opportunity_id: opportunityId,
      account_id: asText(record.AccountId),
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
      salesforce_url: `/lightning/r/Opportunity/${encodeURIComponent(opportunityId)}/view`,
    };
  });

  const closed = records.filter((record) => record.outcome !== "open");
  const open = records.filter((record) => record.outcome === "open");
  const missingList = records.filter(
    (record) => record.list_acv === null || record.list_acv <= 0,
  ).length;
  const missingBooked = records.filter(
    (record) => record.booked_acv === null || record.booked_acv < 0,
  ).length;
  const currencies = [...new Set(records.map((record) => record.currency_iso).filter(Boolean))];
  const closedUsable = closed.filter(
    (record) =>
      record.list_acv !== null &&
      record.list_acv > 0 &&
      record.booked_acv !== null &&
      record.booked_acv >= 0,
  ).length;
  const openUsable = open.filter(
    (record) =>
      record.list_acv !== null &&
      record.list_acv > 0 &&
      record.booked_acv !== null &&
      record.booked_acv >= 0,
  ).length;
  const blockers: string[] = [];
  const warnings: string[] = [];
  if (currencies.length > 1) {
    blockers.push(
      `Multiple Salesforce currencies are present (${currencies.join(", ")}); V1 will not combine them.`,
    );
  }
  if (closedUsable < 30) {
    blockers.push(
      `Only ${closedUsable} usable closed opportunities were found; at least 30 are required.`,
    );
  } else if (closedUsable < 500) {
    warnings.push(
      `${closedUsable} usable closed opportunities support a directional analysis; 500+ per year is the target for stable operating guidance.`,
    );
  }
  if (missingList) {
    warnings.push(
      `${missingList} opportunities have no usable list value. Map an annualized list field or add Opportunity Products.`,
    );
  }
  if (missingBooked) {
    warnings.push(`${missingBooked} opportunities have no usable booked/quoted value.`);
  }
  return {
    records,
    fields,
    readiness: {
      records_fetched: records.length,
      closed_usable: closedUsable,
      open_usable: openUsable,
      missing_list_value: missingList,
      missing_booked_value: missingBooked,
      currencies,
      blockers,
      warnings,
    },
  };
}
