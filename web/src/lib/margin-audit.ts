/**
 * AI pricing and margin audit calculator: the deterministic formula module (PK-107).
 *
 * Spec: docs/design/2026-11-10-ai-margin-audit-calculator.md sections 2 and 3.
 * Pure functions. No React, no fetch, no LLM, no randomness. Every figure is
 * arithmetic on what the visitor typed.
 *
 * Vocabulary (ADR-006, founder decision F1): every cost figure is typed by the
 * visitor, so the basis is declared_cost and the only label is
 * "contribution margin, customer-supplied cost basis". Never gross or net.
 * All label text comes from `labels()`; the basis string is mirrored from
 * pricing/cost_basis.py and a test pins the parity.
 *
 * Never-zero rule: a missing or undefined figure is never returned as 0 or NaN.
 * It is returned as `{ ok: false, reason }`. A typed 0 where the spec allows it
 * (storage cost, included units) is a real answer and is computed with.
 */

// ---------------------------------------------------------------------------
// Named constants (exported so the page can print the formula it ran)
// ---------------------------------------------------------------------------

/** Share of customers modelled at exactly the 90th-percentile usage. */
export const TOP_DECILE_SHARE = 0.1;
/** Band line: below this blended contribution share the band is At risk. A review line, not a benchmark. */
export const AT_RISK_BELOW = 0.4;
/** Band line: below this blended contribution share the band is Watch. A review line, not a benchmark. */
export const WATCH_BELOW = 0.6;
/** Heavy customer within this fraction of break-even usage puts the band at Watch. */
export const BREAK_EVEN_PROXIMITY = 0.5;
/** Expected customer lifetime in months under which the band drops one step. */
export const SHORT_LIFETIME_MONTHS = 12;
/** Usage price leaving less than this share after model cost is UNIT_PRICE_NEAR_COST. */
export const NEAR_COST_SHARE = 0.4;
/** u90 / u_avg at or above this adds the bill-predictability note. */
export const PREDICTABILITY_RATIO = 3;
/** Model-price deflation what-ifs, as fractions. */
export const DEFLATION_STEPS = [0.25, 0.5] as const;
/** Bounds on the heavy-user usage: u_avg <= u90 <= 10 * u_avg. */
export const P90_MAX_MULTIPLE = 10;
/** Relative tolerance so hand-typed boundary inputs (exactly 40%, 1/q = 12) behave as exact. */
const EPS = 1e-9;

/** Default-price blend: 3 input tokens for every 1 output token. */
export const DEFAULT_INPUT_WEIGHT = 0.75;
export const DEFAULT_OUTPUT_WEIGHT = 0.25;

/**
 * Sources for the labelled default provider cost per 1M tokens.
 *
 * The numeric default is deliberately NOT in this module. It must be read from
 * these three public price pages on the day the page is built, using each
 * provider's mid-tier model and the median of the three blends, and recorded
 * with a retrieval date (design section 2.1). It is passed in through
 * `validate(raw, { defaultCostPer1MTokens })`. Until a caller passes it, a blank
 * cost under "1M tokens" is reported as still needed. URLs must be reconfirmed
 * when read. Not read in PK-107: no browser or fetch tool was available.
 */
export const DEFAULT_PRICE_SOURCES = [
  { provider: "OpenAI", url: "https://openai.com/api/pricing/" },
  { provider: "Anthropic", url: "https://www.anthropic.com/pricing" },
  { provider: "Google Gemini", url: "https://ai.google.dev/gemini-api/docs/pricing" },
] as const;

/** Blended price per 1M tokens from an input price and an output price. */
export function blendedPer1MTokens(inputPrice: number, outputPrice: number): number {
  return DEFAULT_INPUT_WEIGHT * inputPrice + DEFAULT_OUTPUT_WEIGHT * outputPrice;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PricingModel = "flat" | "per_seat" | "usage" | "hybrid";
export type UnitKind = "1M tokens" | "other";

export type FieldId =
  | "model"
  | "fee"
  | "seats"
  | "unitPrice"
  | "included"
  | "unit"
  | "unitLabel"
  | "customers"
  | "avgUsage"
  | "p90Usage"
  | "costPerUnit"
  | "otherCost"
  | "churn";

/** What the form holds. null or undefined is blank. Churn is a fraction (0.02 is 2%). */
export interface RawInputs {
  model?: PricingModel | null;
  fee?: number | null;
  seats?: number | null;
  unitPrice?: number | null;
  included?: number | null;
  unit?: UnitKind | null;
  unitLabel?: string | null;
  customers?: number | null;
  avgUsage?: number | null;
  p90Usage?: number | null;
  costPerUnit?: number | null;
  otherCost?: number | null;
  churn?: number | null;
}

export interface ValidateOptions {
  /** The labelled default cost per 1M tokens. Required to resolve a blank cost under "1M tokens". */
  defaultCostPer1MTokens?: number | null;
}

export interface ValidInputs {
  model: PricingModel;
  /** B: flat fee, seat price x seats, or platform fee. null for usage. */
  baseFee: number | null;
  /** p: price per unit (usage) or above the included amount (hybrid). null for flat and per_seat. */
  unitPrice: number | null;
  /** I: included units. null for flat, per_seat and usage. */
  included: number | null;
  unitLabel: string;
  customers: number;
  avgUsage: number;
  p90Usage: number;
  costPerUnit: number;
  otherCost: number;
  churn: number;
}

export type FieldErrorCode =
  | "range"
  | "not_integer"
  | "zero_cost"
  | "zero_churn"
  | "p90_below_avg"
  | "p90_above_multiple"
  | "bad_label"
  | "bad_choice";

export interface FieldError {
  field: FieldId;
  code: FieldErrorCode;
  message: string;
}

export interface ValidationOk {
  ok: true;
  inputs: ValidInputs;
  notes: {
    /** The cost per unit is the labelled default, not the visitor's own figure. */
    defaultCostUsed: boolean;
    /** The visitor typed 0 for storage and other cost: echo "you entered 0". */
    otherCostEnteredZero: boolean;
  };
}

export interface ValidationFail {
  ok: false;
  /** Fields still blank. */
  needed: FieldId[];
  /** Fields filled but invalid. */
  errors: FieldError[];
}

export type Validation = ValidationOk | ValidationFail;

/** A figure that may be unavailable. Never a 0 or NaN stand-in. */
export type Maybe = { ok: true; value: number } | { ok: false; reason: string };

export interface Economics {
  usage: number;
  revenue: number;
  cost: number;
  /** M(u) = Rev(u) - C(u), dollars per customer per month. */
  contribution: number;
  /** M(u) / Rev(u), only when Rev(u) > 0. */
  pct: Maybe;
}

export type BreakEven =
  | { kind: "at"; usage: number }
  | { kind: "negative_before_usage" }
  | { kind: "none" }
  | { kind: "negative_at_every_level" };

export type Band = "negative" | "at_risk" | "watch" | "healthy";
export type Signal =
  | "ADD_USAGE_COMPONENT"
  | "FIX_OVERAGE_OR_ALLOWANCE"
  | "UNIT_PRICE_NEAR_COST"
  | "STRUCTURE_COVERS_P90";

export interface Deflation {
  /** Fraction by which cost per unit falls, 0.25 or 0.5. */
  fall: number;
  blendedPct: number;
}

export interface AuditResult {
  inputs: ValidInputs;
  avg: Economics;
  p90: Economics;
  /** u_bulk = (u_avg - 0.1 u90) / 0.9, the usage of the other 90%. */
  bulkUsage: number;
  breakEven: BreakEven;
  /** u90 / u*, only when a break-even usage exists. */
  p90OverBreakEven: Maybe;
  /** Usage model with p > c: units a month a customer needs to cover storage and other cost, s / (p - c). */
  usageFloor: Maybe;
  monthlyRevenue: number;
  monthlyCost: number;
  /** (R_tot - C_tot) / R_tot. */
  blendedPct: number;
  topDecileShortfall: number;
  /** Share of revenue from customers negative at u90 (a lower bound). 0 when none. */
  revenueAtRiskShare: number;
  /** Cost-covering fee at p90, c * u90 + s. Only for flat and per_seat. */
  costCoveringFee: Maybe;
  signal: Signal;
  /** G5: usage or hybrid with u90 / u_avg >= 3. Not scored. */
  predictabilityNote: boolean;
  /** Band before the churn step. */
  bandBeforeChurn: Band;
  band: Band;
  churnStepApplied: boolean;
  lifetimeMonths: number;
  /** M(u_avg) / q: undiscounted, no acquisition cost. */
  lifetimeContribution: number;
  deflation: Deflation[];
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

interface Range {
  min: number;
  max: number;
  integer?: boolean;
  label: string;
}

const RANGES: Partial<Record<FieldId, Range>> = {
  fee: { min: 0.01, max: 1_000_000, label: "Fee" },
  seats: { min: 1, max: 100_000, integer: true, label: "Average seats per customer" },
  unitPrice: { min: 0.000001, max: 100_000, label: "Price per unit" },
  included: { min: 0, max: 1e12, label: "Units included" },
  customers: { min: 1, max: 100_000, integer: true, label: "Customers" },
  avgUsage: { min: Number.MIN_VALUE, max: 1e12, label: "Average usage" },
  costPerUnit: { min: Number.MIN_VALUE, max: 100_000, label: "Cost per unit" },
  otherCost: { min: 0, max: 1_000_000, label: "Storage and other cost" },
  churn: { min: 0.001, max: 0.5, label: "Monthly churn" },
};

const MODELS: readonly PricingModel[] = ["flat", "per_seat", "usage", "hybrid"];

const isBlank = (v: unknown): boolean => v === undefined || v === null;

function errorText(field: FieldId, code: FieldErrorCode): string {
  const r = RANGES[field];
  switch (code) {
    case "zero_cost":
      return "Cost per unit must be more than 0.";
    case "zero_churn":
      return "Enter at least 0.1%. Zero churn is not something this tool can score.";
    case "p90_below_avg":
      return "A 90th percentile below your average means a few very heavy customers pull the average up. This tool cannot model that shape. Enter a 90th percentile at or above your average, or ask for the audit.";
    case "p90_above_multiple":
      return "Your heavy-customer usage is more than ten times your average, which cannot hold: the top 10% alone would exceed the average. Check both numbers.";
    case "bad_label":
      return "Your unit: enter 1 to 24 characters.";
    case "bad_choice":
      return `${field}: choose one of the listed options.`;
    case "not_integer":
    case "range":
      return `${r ? r.label : field}: enter a ${code === "not_integer" ? "whole " : ""}number from ${r ? r.min : ""} to ${r ? r.max : ""}.`;
  }
}

/**
 * Validate the form. Blanks are never coerced to 0. A failed validation carries
 * no numeric output at all, so the page can render nothing but "Not enough to score."
 */
export function validate(raw: RawInputs, options: ValidateOptions = {}): Validation {
  const needed: FieldId[] = [];
  const errors: FieldError[] = [];
  const fail = (field: FieldId, code: FieldErrorCode) =>
    errors.push({ field, code, message: errorText(field, code) });

  const read = (field: FieldId, value: number | null | undefined): number | null => {
    if (isBlank(value)) {
      needed.push(field);
      return null;
    }
    const r = RANGES[field] as Range;
    const v = value as number;
    if (typeof v !== "number" || !Number.isFinite(v)) {
      fail(field, "range");
      return null;
    }
    if (field === "costPerUnit" && v === 0) {
      fail(field, "zero_cost");
      return null;
    }
    if (field === "churn" && v === 0) {
      fail(field, "zero_churn");
      return null;
    }
    if (v < r.min || v > r.max) {
      fail(field, "range");
      return null;
    }
    if (r.integer && !Number.isInteger(v)) {
      fail(field, "not_integer");
      return null;
    }
    return v;
  };

  // 1. Model
  let model: PricingModel | null = null;
  if (isBlank(raw.model)) needed.push("model");
  else if (MODELS.includes(raw.model as PricingModel)) model = raw.model as PricingModel;
  else fail("model", "bad_choice");

  // 6. Unit. Blank resolves to the visible selection "1M tokens".
  let unitKind: UnitKind = "1M tokens";
  let unitLabel = "1M tokens";
  if (!isBlank(raw.unit)) {
    if (raw.unit === "1M tokens" || raw.unit === "other") unitKind = raw.unit;
    else fail("unit", "bad_choice");
  }
  if (unitKind === "other") {
    if (isBlank(raw.unitLabel)) needed.push("unitLabel");
    else {
      const label = typeof raw.unitLabel === "string" ? raw.unitLabel.trim() : "";
      if (label.length < 1 || label.length > 24) fail("unitLabel", "bad_label");
      else unitLabel = label;
    }
  }

  // 2 to 5. Pricing fields shown for the chosen model.
  let fee: number | null = null;
  let seats: number | null = null;
  let unitPrice: number | null = null;
  let included: number | null = null;
  if (model === "flat" || model === "per_seat" || model === "hybrid") fee = read("fee", raw.fee);
  if (model === "per_seat") seats = read("seats", raw.seats);
  if (model === "usage" || model === "hybrid") unitPrice = read("unitPrice", raw.unitPrice);
  if (model === "hybrid") included = read("included", raw.included);

  // 7, 8, 9
  const customers = read("customers", raw.customers);
  const avgUsage = read("avgUsage", raw.avgUsage);
  let p90Usage: number | null = null;
  if (isBlank(raw.p90Usage)) needed.push("p90Usage");
  else if (
    typeof raw.p90Usage !== "number" ||
    !Number.isFinite(raw.p90Usage) ||
    raw.p90Usage <= 0 ||
    raw.p90Usage > 1e13
  )
    errors.push({ field: "p90Usage", code: "range", message: "Heavy-customer usage: enter a number above 0." });
  else p90Usage = raw.p90Usage;
  if (avgUsage !== null && p90Usage !== null) {
    if (p90Usage < avgUsage) {
      fail("p90Usage", "p90_below_avg");
      p90Usage = null;
    } else if (p90Usage > P90_MAX_MULTIPLE * avgUsage) {
      fail("p90Usage", "p90_above_multiple");
      p90Usage = null;
    }
  }

  // 10. Cost per unit: the single blank that resolves to a value.
  let costPerUnit: number | null = null;
  let defaultCostUsed = false;
  if (isBlank(raw.costPerUnit)) {
    const d = options.defaultCostPer1MTokens;
    if (unitKind === "1M tokens" && typeof d === "number" && Number.isFinite(d) && d > 0) {
      costPerUnit = d;
      defaultCostUsed = true;
    } else needed.push("costPerUnit");
  } else costPerUnit = read("costPerUnit", raw.costPerUnit);

  // 11, 12
  const otherCost = read("otherCost", raw.otherCost);
  const churn = read("churn", raw.churn);

  if (
    needed.length > 0 ||
    errors.length > 0 ||
    model === null ||
    customers === null ||
    avgUsage === null ||
    p90Usage === null ||
    costPerUnit === null ||
    otherCost === null ||
    churn === null
  ) {
    return { ok: false, needed, errors };
  }

  const baseFee =
    model === "usage" ? null : model === "per_seat" ? (fee as number) * (seats as number) : (fee as number);
  return {
    ok: true,
    inputs: {
      model,
      baseFee,
      unitPrice: model === "usage" || model === "hybrid" ? unitPrice : null,
      included: model === "hybrid" ? included : null,
      unitLabel,
      customers,
      avgUsage,
      p90Usage,
      costPerUnit,
      otherCost,
      churn,
    },
    notes: { defaultCostUsed, otherCostEnteredZero: otherCost === 0 },
  };
}

// ---------------------------------------------------------------------------
// Compute
// ---------------------------------------------------------------------------

/** Rev(u): revenue per customer per month at usage u. */
function revenueAt(i: ValidInputs, u: number): number {
  switch (i.model) {
    case "flat":
    case "per_seat":
      return i.baseFee as number;
    case "usage":
      return (i.unitPrice as number) * u;
    case "hybrid":
      return (i.baseFee as number) + (i.unitPrice as number) * Math.max(0, u - (i.included as number));
  }
}

function economics(i: ValidInputs, u: number): Economics {
  const revenue = revenueAt(i, u);
  const cost = i.costPerUnit * u + i.otherCost;
  const contribution = revenue - cost;
  const pct: Maybe =
    revenue > 0
      ? { ok: true, value: contribution / revenue }
      : { ok: false, reason: "No revenue at this usage, so a percentage is not defined." };
  return { usage: u, revenue, cost, contribution, pct };
}

function findBreakEven(i: ValidInputs): BreakEven {
  const c = i.costPerUnit;
  const s = i.otherCost;
  if (i.model === "flat" || i.model === "per_seat") {
    const B = i.baseFee as number;
    return B <= s ? { kind: "negative_before_usage" } : { kind: "at", usage: (B - s) / c };
  }
  if (i.model === "usage") {
    const p = i.unitPrice as number;
    return p > c ? { kind: "none" } : { kind: "negative_at_every_level" };
  }
  const B = i.baseFee as number;
  const p = i.unitPrice as number;
  const I = i.included as number;
  if (B <= s) return { kind: "negative_before_usage" };
  const u1 = (B - s) / c;
  if (u1 <= I) return { kind: "at", usage: u1 };
  if (p < c) return { kind: "at", usage: (B - s - p * I) / (c - p) };
  return { kind: "none" };
}

/**
 * The Margin Health band. First match wins, top to bottom. The churn step is
 * applied by `compute`, not here.
 */
export function band(args: {
  avgContribution: number;
  p90Contribution: number;
  blendedPct: number;
  /** u90 / u*, or null when no break-even usage exists. */
  p90OverBreakEven: number | null;
}): Band {
  const { avgContribution, p90Contribution, blendedPct, p90OverBreakEven } = args;
  if (avgContribution < 0 || blendedPct < 0) return "negative";
  if (blendedPct < AT_RISK_BELOW - EPS || p90Contribution < 0) return "at_risk";
  if (
    blendedPct < WATCH_BELOW - EPS ||
    (p90OverBreakEven !== null && p90OverBreakEven >= BREAK_EVEN_PROXIMITY - EPS)
  )
    return "watch";
  return "healthy";
}

function dropOneStep(b: Band): Band {
  if (b === "healthy") return "watch";
  if (b === "watch") return "at_risk";
  return b;
}

function pickSignal(i: ValidInputs, p90: Economics, be: BreakEven, ratio: number | null): Signal {
  const c = i.costPerUnit;
  if (i.model === "flat" || i.model === "per_seat") {
    if (p90.contribution < 0 || (ratio !== null && ratio >= BREAK_EVEN_PROXIMITY - EPS)) return "ADD_USAGE_COMPONENT";
    return "STRUCTURE_COVERS_P90";
  }
  if (i.model === "hybrid") {
    const p = i.unitPrice as number;
    const I = i.included as number;
    const insideAllowance = be.kind === "negative_before_usage" || (be.kind === "at" && be.usage <= I);
    if (p < c || insideAllowance) return "FIX_OVERAGE_OR_ALLOWANCE";
    return "STRUCTURE_COVERS_P90";
  }
  const p = i.unitPrice as number;
  if ((p - c) / p < NEAR_COST_SHARE - EPS) return "UNIT_PRICE_NEAR_COST";
  return "STRUCTURE_COVERS_P90";
}

/** Compute every figure for validated inputs. Pure and deterministic. */
export function compute(i: ValidInputs): AuditResult {
  const avg = economics(i, i.avgUsage);
  const p90 = economics(i, i.p90Usage);
  const bulkUsage = (i.avgUsage - TOP_DECILE_SHARE * i.p90Usage) / (1 - TOP_DECILE_SHARE);
  const revBulk = revenueAt(i, bulkUsage);

  const monthlyRevenue = i.customers * ((1 - TOP_DECILE_SHARE) * revBulk + TOP_DECILE_SHARE * p90.revenue);
  const monthlyCost = i.customers * (i.costPerUnit * i.avgUsage + i.otherCost);
  const blendedPct = (monthlyRevenue - monthlyCost) / monthlyRevenue;

  const breakEven = findBreakEven(i);
  const ratioValue = breakEven.kind === "at" ? i.p90Usage / breakEven.usage : null;
  const p90OverBreakEven: Maybe =
    ratioValue === null
      ? { ok: false, reason: "No break-even usage exists on these inputs." }
      : { ok: true, value: ratioValue };

  const usageFloor: Maybe =
    i.model === "usage" && (i.unitPrice as number) > i.costPerUnit
      ? { ok: true, value: i.otherCost / ((i.unitPrice as number) - i.costPerUnit) }
      : {
          ok: false,
          reason: "A minimum-usage floor applies only to a usage model whose unit price is above your cost per unit.",
        };

  const costCoveringFee: Maybe =
    i.model === "flat" || i.model === "per_seat"
      ? { ok: true, value: i.costPerUnit * i.p90Usage + i.otherCost }
      : { ok: false, reason: "A cost-covering fee is shown only for flat and per-seat pricing." };

  const topDecileShortfall = TOP_DECILE_SHARE * i.customers * Math.max(0, -p90.contribution);
  const revenueAtRiskShare =
    p90.contribution < 0 ? (TOP_DECILE_SHARE * i.customers * p90.revenue) / monthlyRevenue : 0;

  const bandBeforeChurn = band({
    avgContribution: avg.contribution,
    p90Contribution: p90.contribution,
    blendedPct,
    p90OverBreakEven: ratioValue,
  });
  const lifetimeMonths = 1 / i.churn;
  const churnStepApplied =
    lifetimeMonths < SHORT_LIFETIME_MONTHS - EPS && dropOneStep(bandBeforeChurn) !== bandBeforeChurn;
  const finalBand = churnStepApplied ? dropOneStep(bandBeforeChurn) : bandBeforeChurn;

  const deflation: Deflation[] = DEFLATION_STEPS.map((fall) => ({
    fall,
    blendedPct: 1 - (i.customers * (i.costPerUnit * (1 - fall) * i.avgUsage + i.otherCost)) / monthlyRevenue,
  }));

  return {
    inputs: i,
    avg,
    p90,
    bulkUsage,
    breakEven,
    p90OverBreakEven,
    usageFloor,
    monthlyRevenue,
    monthlyCost,
    blendedPct,
    topDecileShortfall,
    revenueAtRiskShare,
    costCoveringFee,
    signal: pickSignal(i, p90, breakEven, ratioValue),
    predictabilityNote:
      (i.model === "usage" || i.model === "hybrid") && i.p90Usage / i.avgUsage >= PREDICTABILITY_RATIO - EPS,
    bandBeforeChurn,
    band: finalBand,
    churnStepApplied,
    lifetimeMonths,
    lifetimeContribution: avg.contribution / i.churn,
    deflation,
  };
}

/** Validate then compute. A failed validation carries no result. */
export function audit(
  raw: RawInputs,
  options: ValidateOptions = {},
): { validation: ValidationFail } | { validation: ValidationOk; result: AuditResult } {
  const v = validate(raw, options);
  return v.ok ? { validation: v, result: compute(v.inputs) } : { validation: v };
}

// ---------------------------------------------------------------------------
// Labels: the one place label text is written
// ---------------------------------------------------------------------------

/** ADR-006 label for declared_cost. Mirrors LABELS["declared_cost"] in pricing/cost_basis.py; a test pins parity. */
const BASIS_LABEL = "contribution margin, customer-supplied cost basis";

/** Band names. No colour is implied here: colour never carries the band alone. */
export const BAND_NAMES: Record<Band, string> = {
  negative: "Negative",
  at_risk: "At risk",
  watch: "Watch",
  healthy: "Healthy",
};

const BAND_SENTENCES: Record<Band, string> = {
  negative: "On your numbers the average customer costs more than it pays.",
  at_risk: "On your numbers the book is thin, or your heaviest customers cost more than they pay.",
  watch:
    "On your numbers contribution is thin, or your heavy customers are within a factor of two of the usage level where they turn negative.",
  healthy:
    "On your numbers contribution clears our review lines. That says nothing about how you compare with other companies.",
};

const money = (n: number): string =>
  "$" + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pctText = (fraction: number): string => (fraction * 100).toFixed(1);
const numText = (n: number): string =>
  Math.abs(n) >= 1
    ? n.toLocaleString("en-US", { maximumFractionDigits: 2 })
    : n.toLocaleString("en-US", { maximumSignificantDigits: 3 });

export interface Labels {
  state: "scored";
  /** S6. Present wherever a contribution figure appears. */
  basis: string;
  /** S7. */
  basisNote: string;
  bandName: string;
  bandSentence: string;
  churnNote: string | null;
  avg: string;
  p90: string;
  breakEven: string;
  breakEvenRatio: string | null;
  usageFloor: string | null;
  revenueAtRisk: string;
  blended: string;
  deflation: string;
  signal: string;
  predictability: string | null;
  bandLines: string;
  /** Echo of a typed 0 for storage and other cost, else null. */
  otherCostEcho: string | null;
}

export interface NotScoredLabels {
  state: "not_enough";
  headline: string;
  stillNeeded: string | null;
  errors: string[];
}

const FIELD_NAMES: Record<FieldId, string> = {
  model: "How you charge",
  fee: "Fee",
  seats: "Average seats per customer",
  unitPrice: "Price per unit",
  included: "Units included",
  unit: "Your unit",
  unitLabel: "Unit label",
  customers: "Customers",
  avgUsage: "Average usage per customer",
  p90Usage: "Usage of a heavy customer",
  costPerUnit: "Model-provider cost per unit",
  otherCost: "Storage and other cost",
  churn: "Monthly churn",
};

/**
 * Every user-facing string this module produces. Call with a failed validation
 * for the "Not enough to score." state (no figure is rendered), or with a
 * result for the scored state.
 */
export function labels(x: ValidationFail): NotScoredLabels;
export function labels(x: AuditResult, notes?: Partial<ValidationOk["notes"]>): Labels;
export function labels(
  x: ValidationFail | AuditResult,
  notes: Partial<ValidationOk["notes"]> = {},
): Labels | NotScoredLabels {
  if ("needed" in x) {
    return {
      state: "not_enough",
      headline: "Not enough to score.",
      stillNeeded: x.needed.length > 0 ? `Still needed: ${x.needed.map((f) => FIELD_NAMES[f]).join(", ")}.` : null,
      errors: x.errors.map((e) => e.message),
    };
  }
  const r = x;
  const unit = r.inputs.unitLabel;
  const figure = (who: string, e: Economics): string => {
    const verb = e.contribution < 0 ? "loses" : "leaves";
    const share = e.pct.ok ? ` (${pctText(e.pct.value)}%)` : "";
    return `${who} ${verb} ${money(e.contribution)} a month${share}.`;
  };

  let breakEven: string;
  switch (r.breakEven.kind) {
    case "at":
      breakEven = `Contribution turns negative above ${numText(r.breakEven.usage)} ${unit} a month per customer.`;
      break;
    case "negative_before_usage":
      breakEven = "Contribution is negative before any usage: the fee does not cover storage and other cost.";
      break;
    case "none":
      breakEven = "No break-even: each extra unit earns more than it costs.";
      break;
    case "negative_at_every_level":
      breakEven = "Negative at every level of usage: each unit costs at least what it earns.";
      break;
  }

  const [d25, d50] = r.deflation;
  let signal: string;
  switch (r.signal) {
    case "ADD_USAGE_COMPONENT":
      signal = `A flat or per-seat price leaves your heavy customers uncovered. Look at a usage component or an included-usage limit. A fee of at least ${
        r.costCoveringFee.ok ? money(r.costCoveringFee.value) : ""
      } would cover a 90th-percentile customer's cost on these inputs. What to charge is your decision.`;
      break;
    case "FIX_OVERAGE_OR_ALLOWANCE":
      signal =
        "Your hybrid structure leaks. Either the price above the included amount is below your cost per unit, or contribution turns negative inside the included amount. Look at both.";
      break;
    case "UNIT_PRICE_NEAR_COST":
      signal = `Your unit price leaves less than ${Math.round(NEAR_COST_SHARE * 100)} cents of each dollar after model cost. Look at the unit price or the cost per unit.`;
      break;
    case "STRUCTURE_COVERS_P90":
      signal = "On these inputs your structure covers a 90th-percentile customer's cost.";
      break;
  }

  const months = r.lifetimeMonths.toFixed(1);
  return {
    state: "scored",
    basis: BASIS_LABEL,
    basisNote: "The cost figures are yours. Pricekeel has not checked them against a billing or cost system.",
    bandName: BAND_NAMES[r.band],
    bandSentence: BAND_SENTENCES[r.band],
    churnNote: r.churnStepApplied
      ? `Monthly churn of ${pctText(r.inputs.churn)}% means a customer lasts about ${months} months on average, so thin contribution has little time to compound. The band was lowered one step for that.`
      : null,
    avg: figure("An average customer", r.avg),
    p90: figure("A customer at the 90th percentile", r.p90),
    breakEven,
    breakEvenRatio: r.p90OverBreakEven.ok
      ? `Your heavy customer is at ${numText(r.p90OverBreakEven.value)} times that level.`
      : null,
    usageFloor: r.usageFloor.ok
      ? `Each customer must use at least ${numText(r.usageFloor.value)} ${unit} a month to cover storage and other cost.`
      : null,
    revenueAtRisk:
      r.revenueAtRiskShare > 0
        ? `At least ${pctText(r.revenueAtRiskShare)}% of revenue comes from customers who cost more than they pay at the 90th percentile.`
        : "No revenue sits with customers who cost more than they pay at the 90th percentile.",
    blended: `Across your book, contribution is ${pctText(r.blendedPct)}% of revenue on these inputs.`,
    deflation: `If your model cost per unit fell by 25%, contribution on these inputs would move from ${pctText(r.blendedPct)}% to ${pctText(d25.blendedPct)}%. If it fell by 50%, to ${pctText(d50.blendedPct)}%. Prices held. This is a what-if on your numbers, not a forecast of what providers will charge.`,
    signal,
    predictability: r.predictabilityNote
      ? "A customer at the 90th percentile pays at least three times the average bill. Whether your buyers accept that is a question for them, not for this tool."
      : null,
    bandLines: `Bands: Negative below 0%. At risk below ${Math.round(AT_RISK_BELOW * 100)}%. Watch below ${Math.round(WATCH_BELOW * 100)}%. These are our review lines, not industry benchmarks.`,
    otherCostEcho: notes.otherCostEnteredZero ? "You entered 0 for storage and other cost." : null,
  };
}
