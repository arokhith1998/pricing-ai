// Client for the Pricekeel FastAPI service. Server-side base URL (no secrets).
// Default to 127.0.0.1 (not localhost): on Windows, localhost can resolve to
// IPv6 first and miss an IPv4-only uvicorn.
import sampleFallback from "@/data/sample-fallback.json";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

export type Overview = {
  opportunities: number;
  won: number;
  lost: number;
  win_rate: number;
  resolved_accounts: number;
  booked_acv_won: number;
  price_realization_won: number;
  avg_discount_won: number;
};

export type Leakage = {
  policy_threshold: number;
  reference_threshold: number;
  gross_discount_won: number;
  off_policy_leakage_won: number;
  excess_vs_reference_won: number;
  excess_pct_of_booked: number;
  deals_above_reference: number;
};

export type WinRateBand = {
  discount_band: string;
  deals: number;
  won: number;
  avg_discount: number;
  win_rate: number;
};

export type SegmentRow = {
  segment: string;
  deals: number;
  list_acv: number;
  booked_acv: number;
  avg_discount: number;
  price_realization: number;
};

// A "slice" row for any dimension (segment, business_unit, product_line, ...).
// The dimension's string value lives under the dimension's name as a key.
export type SliceRow = {
  deals: number;
  list_acv: number;
  booked_acv: number;
  avg_discount: number;
  price_realization: number;
} & Record<string, string | number>;

export type LeakDeal = {
  opportunity_id: string;
  resolved_account_name: string;
  segment: string;
  rep_id: string;
  list_acv: number;
  booked_acv: number;
  discount_pct: number;
  competitor_present: boolean;
  is_quarter_end: boolean;
  off_policy_unapproved: boolean;
  excess_discount_dollars: number;
};

export type QuarterEnd = {
  qe_deals: number;
  qe_avg_discount: number;
  rest_avg_discount: number;
  lift: number;
  attributable_discount_won: number;
} | null;

export type Governance = {
  off_policy_won: number;
  off_policy_unapproved_won: number;
  unapproved_discount_dollars: number;
};

export type ReferenceDiscount = {
  reference_threshold: number;
  reference_band: string;
  peak_win_rate: number;
  peak_band: string;
  // [point, low, high] per discount band
  band_win_rate_ci: Record<string, [number, number, number]>;
};

export type PackagingSignal = {
  dimension: string;
  value: string;
  price_realization: number;
  median_realization: number;
  gap_pp: number;
  deals: number;
  booked_acv: number;
};

export type TradeOrGive = {
  deals: number;
  dollars: number;
  median_term_months: number;
  off_policy_total: number;
};

// The actual no-trade deals behind the trade_or_give count (the receipts).
export type TradeOrGiveDeal = {
  opportunity_id: string;
  resolved_account_name: string;
  segment: string;
  list_acv: number;
  booked_acv: number;
  discount_pct: number;
  discount_amount: number;
  term_months: number | null;
};

// Per-finding receipts: the deals behind the quarter-end and packaging signals.
export type FindingDeal = {
  opportunity_id: string;
  resolved_account_name: string;
  segment: string;
  list_acv: number;
  booked_acv: number;
  discount_pct: number;
  discount_amount: number;
};

// Sales-friendly split of won deals: discount earned vs discount worth
// investigating. Added 2026-05-30 per the expert review — reports historical
// fact, no recovery-rate assumption. See pricing/metrics.defended_vs_investigate.
export type DefendedVsInvestigate = {
  reference_threshold: number;
  defended_value: number;
  defended_deals: number;
  investigate_value: number;
  investigate_deals: number;
  defended_pct_of_booked: number;
};

export type Diagnostic = {
  overview: Overview;
  leakage: Leakage;
  reference_discount: ReferenceDiscount;
  quarter_end: QuarterEnd;
  governance: Governance;
  win_rate_by_band: WinRateBand[];
  realization_by_segment: SegmentRow[];
  top_leak_deals: LeakDeal[];
  // Optional hierarchy: dimension name -> rows. Empty {} if no hierarchy
  // columns are populated in the dataset.
  hierarchy_slices: Record<string, SliceRow[]>;
  // Framework signals (Rivera packaging, Simon-Kucher trade-or-give).
  packaging_signals: PackagingSignal[];
  trade_or_give: TradeOrGive;
  trade_or_give_deals: TradeOrGiveDeal[];
  quarter_end_deals: FindingDeal[];
  packaging_signal_deals: FindingDeal[];
  // Defended-vs-investigate split (added 2026-05-30 per expert review).
  defended_vs_investigate: DefendedVsInvestigate;
};

export type ModelInfo = {
  metrics: {
    n_train: number;
    n_test: number;
    auc: number;
    avg_precision: number;
    brier: number;
    base_rate: number;
    mean_pred: number;
  };
  feature_importance: { feature: string; label: string; share: number }[];
  model_leakage: {
    deals: number;
    mean_justified_discount: number;
    mean_actual_discount: number;
    model_excess_won: number;
    deals_over_justified: number;
    model_excess_pct_of_booked: number;
  };
};

export type Deal = {
  opportunity_id: string;
  resolved_account_name: string;
  segment: string;
  industry: string;
  product_tier: string;
  list_acv: number;
  discount_pct: number;
  competitor_present: boolean;
  is_quarter_end: boolean;
};

export type Factor = {
  label: string;
  value: string;
  direction: "up" | "down";
  contribution: number;
};

export type CurvePoint = { discount: number; win_prob: number; expected_acv: number };

// The evidence behind a recommendation (explainability panel, Phase 3).
export type ComparableDeal = {
  opportunity_id: string;
  resolved_account_name: string;
  segment: string;
  industry?: string;
  list_acv: number;
  discount_pct: number;
  is_won: boolean;
};

export type BandContext = {
  segment: string;
  cohort_deals: number;
  bands: { band: string; deals: number; win_rate: number }[];
  current_band: string;
  recommended_band: string;
};

export type Confidence = {
  auc: number;
  mean_pred: number;
  base_rate: number;
  n_train: number;
};

export type Recommendation = {
  opportunity_id: string;
  account: string;
  segment: string;
  list_acv: number;
  current_discount: number;
  recommended_discount: number;
  win_prob_at_current: number;
  win_prob_at_rec: number;
  expected_acv_at_current: number;
  expected_acv_at_rec: number;
  uplift: number;
  top_factors: Factor[];
  comparables: ComparableDeal[];
  band_context: BandContext;
  confidence: Confidence;
  curve: CurvePoint[];
};

// Hung backends should fail the page fast (and let /sample fall back to the
// bundled snapshot) instead of stalling SSR until the platform kills it.
const API_TIMEOUT_MS = 8_000;

// Shared-secret header for the FastAPI service. Empty string when unset so
// local dev keeps working against an unsecured uvicorn.
const API_KEY_HEADER = { "X-Pricekeel-Key": process.env.PRICEKEEL_API_KEY ?? "" };

// All server-side calls to the FastAPI backend funnel through here: 8s
// AbortController timeout + the X-Pricekeel-Key header on every request.
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(`${API}${path}`, {
      cache: "no-store",
      ...init,
      headers: { ...API_KEY_HEADER, ...(init?.headers ?? {}) },
      signal: ctrl.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await apiFetch(path);
  if (!res.ok) throw new Error(`API responded ${res.status} for ${path}`);
  return res.json();
}

export const getDemo = (policy = 0.15) =>
  getJSON<Diagnostic>(`/demo?policy=${policy}`);

// Bundled snapshot of the demo diagnostic payload (policy 0.15), generated by
// running pricing.diagnostic.run on data/synthetic/deals.csv and serializing
// exactly what GET /demo returns. Regenerate when the sample dataset or the
// payload shape changes. The cast is needed because JSON imports widen tuple
// types like band_win_rate_ci to number[].
const SAMPLE_FALLBACK = sampleFallback as unknown as Diagnostic;

// Demo payload for /sample with a bundled fallback: if the FastAPI backend is
// down or times out, return the snapshot (flagged `cached: true` so the page
// can render an honest "cached sample" note) instead of erroring. The
// snapshot was generated at the default policy of 0.15, so any other policy
// still requires the live API.
export async function getDemoWithFallback(
  policy = 0.15,
): Promise<{ data: Diagnostic; cached: boolean }> {
  try {
    return { data: await getDemo(policy), cached: false };
  } catch (err) {
    if (policy !== 0.15) throw err;
    return { data: SAMPLE_FALLBACK, cached: true };
  }
}

export const getModel = () => getJSON<ModelInfo>("/model");

export const getDeals = (limit = 40) =>
  getJSON<{ deals: Deal[] }>(`/deals?limit=${limit}`).then((d) => d.deals);

export async function getRecommendation(
  opportunity_id: string,
): Promise<Recommendation> {
  const res = await apiFetch("/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ opportunity_id }),
  });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  return res.json();
}

export async function getSummary(
  policy = 0.15,
): Promise<{ enabled: boolean; summary: string | null }> {
  const res = await apiFetch("/summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
  });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  return res.json();
}
