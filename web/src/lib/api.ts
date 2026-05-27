// Client for the Pricekeel FastAPI service. Server-side base URL (no secrets).
// Default to 127.0.0.1 (not localhost): on Windows, localhost can resolve to
// IPv6 first and miss an IPv4-only uvicorn.
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

export type Diagnostic = {
  overview: Overview;
  leakage: Leakage;
  reference_discount: ReferenceDiscount;
  quarter_end: QuarterEnd;
  governance: Governance;
  win_rate_by_band: WinRateBand[];
  realization_by_segment: SegmentRow[];
  top_leak_deals: LeakDeal[];
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
  curve: CurvePoint[];
};

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API responded ${res.status} for ${path}`);
  return res.json();
}

export const getDemo = (policy = 0.15) =>
  getJSON<Diagnostic>(`/demo?policy=${policy}`);

export const getModel = () => getJSON<ModelInfo>("/model");

export const getDeals = (limit = 40) =>
  getJSON<{ deals: Deal[] }>(`/deals?limit=${limit}`).then((d) => d.deals);

export async function getRecommendation(
  opportunity_id: string,
): Promise<Recommendation> {
  const res = await fetch(`${API}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ opportunity_id }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  return res.json();
}

export async function getSummary(
  policy = 0.15,
): Promise<{ enabled: boolean; summary: string | null }> {
  const res = await fetch(`${API}/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API responded ${res.status}`);
  return res.json();
}
