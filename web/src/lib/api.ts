// Client for the Pricekeel FastAPI service. Server-side base URL (no secrets).
// Default to 127.0.0.1 (not localhost): on Windows, localhost can resolve to
// IPv6 first and miss an IPv4-only uvicorn.
import sampleFallback from "@/data/sample-fallback.json";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

// Thrown instead of a plain Error whenever the FastAPI backend answers with a
// non-2xx status, so callers can tell a bad request apart from a backend
// that is actually down. 4xx means the backend understood the request and
// rejected it (bad opportunity_id, a discount outside the scoring grid, a
// validation failure): the fix is in the input, not the connection. 5xx or a
// network failure (timeout, connection refused) means the backend itself is
// unreachable or erroring: the fix is not something the caller's input can
// change. `detail` carries the upstream's own message when the body was
// JSON with a `detail` or `error` string (FastAPI's HTTPException shape, or
// this app's own Response.json({ error }) shape), so a specific validation
// message survives the trip instead of collapsing into "is the API running?".
export class ApiError extends Error {
  status: number;
  isClientError: boolean;
  detail?: string;

  constructor(status: number, detail?: string) {
    super(detail ? `API responded ${status}: ${detail}` : `API responded ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.isClientError = status >= 400 && status < 500;
    this.detail = detail;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const body: unknown = await res.clone().json();
    if (body && typeof body === "object") {
      const b = body as Record<string, unknown>;
      detail =
        typeof b.detail === "string" ? b.detail : typeof b.error === "string" ? b.error : undefined;
    }
  } catch {
    // Body was not JSON, or already consumed. Status-only message is fine.
  }
  return new ApiError(res.status, detail);
}

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
  // Single-global-reference lens. Overstates: it measures every segment
  // against one reference threshold, even segments whose own win point sits
  // above it. Kept as a labeled secondary figure, never the headline.
  excess_vs_reference_won: number;
  excess_pct_of_booked: number;
  deals_above_reference: number;
  // Segment-aware lens: each deal measured against its own segment's
  // reference where the segment earned one. This is the headline figure.
  excess_vs_segment_reference_won?: number;
  excess_segment_pct_of_booked?: number;
  deals_above_segment_reference?: number;
  // When the book is too sparse for reference_discount() to compute a
  // reference at all, the backend returns every excess figure above as 0.0
  // with excess_basis "insufficient data" and excess_disclosure carrying the
  // human-readable reason (band counts, etc). That 0.0 is NOT a finding of
  // "no pricing upside": it means the book does not support the estimate
  // yet. Every surface showing these dollar figures must check excess_basis
  // and render excess_disclosure instead of a bare $0 when it is set.
  excess_basis?: string;
  excess_disclosure?: string;
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

// Per-value-metric reference discount partition (UBP MVP). Each row is the
// reference band computed within deals sharing a value metric (seats,
// consumption, hybrid, ...), since a single book-wide reference threshold can
// blend metrics with different willingness to pay. See CONTRACT C.
export type ValueMetricReference = {
  value_metric: string;
  deals: number;
  bands_populated: number;
  reference_threshold: number;
  reference_band: string;
  basis: string;
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
  // "insufficient data" when the book was too sparse to compute a reference
  // at all; both value/deal counts above are 0 in that case, not a $0 finding.
  reference_basis?: string;
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
  // Per-value-metric reference discount partition (CONTRACT C). Optional so
  // cached/pre-contract API responses still render.
  value_metric_reference?: ValueMetricReference[];
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
    // Brier of a constant that just quotes the training book's win rate, and
    // the model's skill against it. Positive skill is what earns the right to
    // show a per-deal probability at all; the mean_pred/base_rate pair above
    // is an average that a constant predictor matches perfectly.
    brier_constant?: number;
    brier_skill?: number;
    // Which holdout produced these numbers: "time" (the latest closes, so the
    // model is graded on deals that closed after everything it trained on) or
    // "random_stratified", the fallback when close dates are unusable. Optional
    // so a cached pre-contract API response still renders.
    split?: string;
    test_from?: string | null;
  };
  feature_importance: { feature: string; label: string; share: number }[];
  model_leakage: {
    deals: number;
    mean_justified_discount: number;
    mean_actual_discount: number;
    // Total across modeled_value + floor_based_value, kept for callers
    // written before the split below. Do not headline this alone: 61% of it
    // on the demo book is Enterprise, where every justified discount is a
    // support-floor edge, not a modeled curve (mle-reviewer, 2026-09-27).
    model_excess_won: number;
    deals_over_justified: number;
    model_excess_pct_of_booked: number;
    // The only component that is actually a model output: an interior EV-
    // curve peak with real win-probability movement. Headline this one.
    // Optional so an older cached payload (pre-split) still renders.
    modeled_value?: { excess: number; deals: number; pct_of_booked: number };
    // A band-guardrail median or a support-floor edge, never a curve peak.
    // Disclose, never headline.
    floor_based_value?: { excess: number; deals: number; pct_of_booked: number };
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
  // See ModelInfo.metrics.split. A random-split fallback must never be
  // described to the user as validation on later deals.
  split?: string;
  test_from?: string | null;
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
  // None for "support_floor" and "no_discount_on_record": the model measured
  // no discount effect there, so a dollar "gain" would be invented rather
  // than modeled (mle-reviewer, 2026-09-27). Optional for cached payloads
  // from before uplift could be null.
  uplift: number | null;
  // Only "support_floor" carries this: list ACV times the discount points
  // not added at the floor (current minus recommended), always >= 0 since a
  // floor never adds discount. Render as "price retained if the floor
  // holds", never as expected value gain. Optional for cached payloads.
  price_retained?: number | null;
  top_factors: Factor[];
  comparables: ComparableDeal[];
  band_context: BandContext;
  confidence: Confidence;
  curve: CurvePoint[];
  // How the recommended discount was derived: "modeled_ev_curve" (an interior
  // EV-curve peak with real win-probability movement), "band_guardrail"
  // (too few comparable deals, caps at the cohort's observed median), or
  // "support_floor" (the model path's own edge case: the clipped EV-curve
  // argmax lands on the edge of the cohort's support, or the curve barely
  // moves; never a modeled peak, and never adds discount). Optional so older
  // cached payloads still render.
  method?: string;
  // The correlational-not-causal caveat that belongs next to the uplift
  // figure: the strongest dollar claim on the page. Optional for the same
  // cached-payload reason.
  caveat?: string;
  // top_factors above is evaluated at the deal's current discount;
  // top_factors_at_recommended is the same explanation at the row the
  // headline actually recommends. Optional: older payloads omit it.
  top_factors_at_recommended?: Factor[];
  // True when the recommended discount sits at the edge of the scored grid
  // (so the "optimum" may just be where the grid stopped, not a real peak).
  at_grid_edge?: boolean;
  // True only for "support_floor" when the deal's own discount sits entirely
  // below the cohort's clipped grid: no curve applies at all, a distinct
  // claim from "the floor of the range is the peak" (mle-reviewer, 2026-09-27).
  below_support?: boolean;
  // Disclosed: whether this deal's row was in the training partition rather
  // than the holdout the model's own metrics were scored on. A win
  // probability shown for an in-sample deal is optimistic relative to a
  // genuinely held-out one (mle-reviewer, 2026-09-27).
  in_sample?: boolean;
};

// --- Governance loop (exceptions + digest) ---------------------------------
// Contract fixed 2026-06-11; the FastAPI side implements it in parallel.
// UNLIKE every other pct field in this file, discount/floor/realization
// figures on this contract are percent on the 0-100 scale (18 = 18%), both
// in the POST body and in the verdict/digest responses. Format them with
// pct100, never pct/pct0. EV deltas and excess are dollars. Win
// probabilities are also percent 0-100.

export type ExceptionVerdict = {
  requested_pct: number;
  recommended_pct: number;
  floor_pct: number;
  below_floor: boolean;
  ev_delta_vs_recommended: number;
  win_prob_at_requested: number;
  win_prob_at_recommended: number;
  rationale: string;
};

export type ExceptionInput = {
  deal_id: string;
  requested_discount_pct: number;
  justification: string;
  requested_by: string;
};

// POST /exceptions response: the verdict plus the log entry's identity.
// `persisted` (api/routers/governance.py) is true only when the decision
// landed in the durable store; false means it fell back to the in-memory
// log (DATABASE_URL unset/unreachable) and will not survive a restart.
// Optional so an older cached response still parses.
export type ExceptionResult = {
  id: string;
  verdict: ExceptionVerdict;
  created_at: string;
  persisted?: boolean;
};

// GET /exceptions items: the original request fields plus verdict + created_at.
export type ExceptionRecord = ExceptionInput & {
  verdict: ExceptionVerdict;
  created_at: string;
};

export type Digest = {
  customer: string;
  generated_at: string;
  window_days: number;
  headline: string;
  lines: string[];
  stats: {
    exceptions_total: number;
    exceptions_below_floor: number;
    copilot_decisions: number;
    realization_pct: number;
    excess_vs_segment_reference: number;
  };
  // Where the book-level realization/leakage figures in `stats` came from.
  // "demo" means the sample book, not the recipient's own Salesforce data;
  // the digest email must disclose that. Optional so a pre-contract cached
  // response still renders (treated as non-demo).
  book_source?: "demo" | "live";
};

// Copilot canonical-question answer, mirrored from pricing/copilot.py's
// Answer.to_dict(). `narrated` is optional so an older cached response (from
// before this field existed) still types-check; treat a missing value as
// narrated (the pre-2026-09-27 behavior). `narrated: false` means no LLM
// provider is configured on this server: `text` is the deterministic
// engine's own fallback line, not model-generated prose, and callers must
// label it as such rather than presenting it as a normal chat reply.
export type CopilotAnswer = {
  text: string;
  opportunities: unknown[];
  qid: string;
  citations_used: string[];
  degraded: boolean;
  degraded_keys: string[];
  non_additive: string;
  narrated?: boolean;
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

async function getJSON<T>(path: string, headers?: Record<string, string>): Promise<T> {
  const res = await apiFetch(path, headers ? { headers } : undefined);
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

// The decision log is scoped per customer. The web proxy passes the verified
// access code, or a per-visitor demo:<uuid> (gate.ts) for lead-only demo
// visitors, as this header; the governance store filters reads and tags
// writes by it. (2026-09-27: this used to say "default" for demo visitors,
// stale since gate.ts started minting a distinct demo:<uuid> per visitor.)
const CUSTOMER_HEADER = "X-Pricekeel-Customer";

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
  customer = "default",
): Promise<Recommendation> {
  const res = await apiFetch("/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json", [CUSTOMER_HEADER]: customer },
    body: JSON.stringify({ opportunity_id }),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

// Price an exception request (or log an approval at the recommended discount)
// and get the verdict back. The backend logs the entry either way; the verdict
// says whether the request sits below the policy floor and what it costs.
export async function postException(
  input: ExceptionInput,
  customer = "default",
): Promise<ExceptionResult> {
  const res = await apiFetch("/exceptions", {
    method: "POST",
    headers: { "Content-Type": "application/json", [CUSTOMER_HEADER]: customer },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export const getExceptions = (limit = 50, customer = "default") =>
  getJSON<{ items: ExceptionRecord[] }>(`/exceptions?limit=${limit}`, {
    [CUSTOMER_HEADER]: customer,
  });

export const getDigest = (customer = "default") =>
  getJSON<Digest>("/digest", { [CUSTOMER_HEADER]: customer });

// One digest per real customer with decision-log activity in the last 7
// days, excluding demo:* tenants (2026-09-27 fix). GET /digest is scoped to
// a single tenant via X-Pricekeel-Customer, which is why the cron sender
// used to always hit "default" and get zero activity back once no one wrote
// to that tenant anymore; this walks every active tenant server-side instead.
export const getDigestAll = () =>
  getJSON<{ digests: Digest[]; customers: string[] }>("/digest/all");

export async function getSummary(
  policy = 0.15,
): Promise<{ enabled: boolean; summary: string | null }> {
  const res = await apiFetch("/summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}
