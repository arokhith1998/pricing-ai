// Everything the landing page shows about the synthetic 2,000-deal book is
// derived here, from src/data/sample-fallback.json, and nowhere else. Nothing
// on the page is typed by hand: regenerate the snapshot (see src/lib/api.ts)
// and every figure, the chosen deal and the probe move on their own.
//
// Pure functions, no I/O, no API calls: the landing route stays force-static.
import sampleFallback from "@/data/sample-fallback.json";
import type { Diagnostic, LeakDeal } from "@/lib/api";

export const SAMPLE = sampleFallback as unknown as Diagnostic;

// Segment-aware excess is the headline lens (pricing-strategist review,
// 2026-09-27). It falls back to the global figure only when an older cached
// payload lacks the segment-aware field.
export const HERO_EXCESS =
  SAMPLE.leakage.excess_vs_segment_reference_won ?? SAMPLE.leakage.excess_vs_reference_won;

export const SYNTHETIC_DEAL_TAG = "Synthetic sample deal. Figures from the bundled synthetic snapshot.";

// --- The deal rule ---------------------------------------------------------
// DEAL RULE: of the deals in `top_leak_deals`, take the one with the largest
// `excess_discount_dollars`; if two tie, the lower `opportunity_id` wins.
// It is a function of the data only (no randomness, no clock, no index into an
// unsorted list), so the same snapshot always yields the same deal and a
// regenerated snapshot yields the next biggest exception, not an arbitrary one.
export function selectSampleDeal(deals: readonly LeakDeal[]): LeakDeal {
  if (deals.length === 0) throw new Error("selectSampleDeal: no deals in the snapshot");
  return deals.reduce((best, d) => {
    if (d.excess_discount_dollars !== best.excess_discount_dollars) {
      return d.excess_discount_dollars > best.excess_discount_dollars ? d : best;
    }
    return d.opportunity_id < best.opportunity_id ? d : best;
  });
}

// --- Bands ------------------------------------------------------------------
export type ProbeBand = {
  label: string;
  deals: number;
  won: number;
  winRate: number;
  ciLow: number;
  ciHigh: number;
};

// The probe reads two snapshot fields and nothing else: win_rate_by_band and
// reference_discount.band_win_rate_ci ([point, low, high] per band).
export function buildProbeBands(sample: Diagnostic): ProbeBand[] {
  const ci = sample.reference_discount.band_win_rate_ci;
  return sample.win_rate_by_band.map((b) => {
    const entry = ci[b.discount_band];
    return {
      label: b.discount_band,
      deals: b.deals,
      won: b.won,
      winRate: b.win_rate,
      ciLow: entry ? entry[1] : b.win_rate,
      ciHigh: entry ? entry[2] : b.win_rate,
    };
  });
}

// The win point on the probe is the band with the highest win rate.
export function peakBandLabel(bands: readonly ProbeBand[]): string {
  return bands.reduce((best, b) => (b.winRate > best.winRate ? b : best)).label;
}

// "25%+" -> 25, "5-10%" -> 5: the band's lower edge, in percent points.
function lowerEdge(label: string): number {
  return parseFloat(label);
}

// The band a discount (a 0 to 1 fraction) falls in.
export function bandForDiscount(discount: number, labels: readonly string[]): string {
  const points = discount * 100;
  const sorted = [...labels].sort((a, b) => lowerEdge(a) - lowerEdge(b));
  let found = sorted[0];
  for (const l of sorted) if (lowerEdge(l) <= points) found = l;
  return found;
}

// --- Page fingerprint ---------------------------------------------------------
// NOT the engine's evidence_version. The engine stamps that on a live verdict
// (sha256 of book, policy, method and code); the bundled snapshot carries none,
// so this page never shows one. This is a fingerprint of the figures the page
// renders, 16 hex characters, so a reader can see when they change. Two FNV-1a
// lanes, no crypto import, so it is safe in any bundle.
export function fingerprint(text: string): string {
  let a = 0x811c9dc5;
  let b = 0x01000193 ^ 0xdeadbeef;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    a = Math.imul(a ^ c, 0x01000193) >>> 0;
    b = Math.imul(b ^ c, 0x85ebca6b) >>> 0;
    b = (b ^ (b >>> 13)) >>> 0;
  }
  return a.toString(16).padStart(8, "0") + b.toString(16).padStart(8, "0");
}

// --- The decision record ----------------------------------------------------
type SegmentReference = {
  segment: string;
  reference_threshold: number;
  reference_band: string;
  basis: string;
};

export type DecisionRecord = {
  opportunityId: string;
  segment: string;
  listAcv: number;
  bookedAcv: number;
  requestedDiscount: number;
  excessDollars: number;
  priceRealization: number;
  quarterEnd: boolean;
  competitorPresent: boolean;
  requestedBand: ProbeBand;
  referenceBand: ProbeBand;
  referenceBandLabel: string;
  referenceBasis: string;
  peakBandLabel: string;
  peakWinRate: number;
  method: string;
  pageFingerprint: string;
};

// The record carries an opportunity id and a segment and never the account
// name: the snapshot's names are synthetic company-like strings and must not
// read as a customer logo.
export function buildDecisionRecord(sample: Diagnostic): DecisionRecord {
  const deal = selectSampleDeal(sample.top_leak_deals);
  const bands = buildProbeBands(sample);
  const refs = (sample.leakage as unknown as { segment_references?: SegmentReference[] })
    .segment_references;
  const segRef = refs?.find((r) => r.segment === deal.segment);
  const referenceBandLabel = segRef?.reference_band ?? sample.reference_discount.reference_band;
  const referenceBasis = segRef?.basis ?? "own win point";
  const byLabel = (l: string) => bands.find((b) => b.label === l) ?? bands[0];
  const requestedBand = byLabel(
    bandForDiscount(
      deal.discount_pct,
      bands.map((b) => b.label),
    ),
  );
  const referenceBand = byLabel(referenceBandLabel);
  const peak = bands.find((b) => b.label === peakBandLabel(bands)) ?? bands[0];
  const method = `${referenceBasis.charAt(0).toUpperCase()}${referenceBasis.slice(1)}, correlational`;
  return {
    opportunityId: deal.opportunity_id,
    segment: deal.segment,
    listAcv: deal.list_acv,
    bookedAcv: deal.booked_acv,
    requestedDiscount: deal.discount_pct,
    excessDollars: deal.excess_discount_dollars,
    priceRealization: deal.booked_acv / deal.list_acv,
    quarterEnd: deal.is_quarter_end,
    competitorPresent: deal.competitor_present,
    requestedBand,
    referenceBand,
    referenceBandLabel,
    referenceBasis,
    peakBandLabel: peak.label,
    peakWinRate: peak.winRate,
    method,
    pageFingerprint: fingerprint(
      JSON.stringify([deal.opportunity_id, deal.discount_pct, method, bands]),
    ),
  };
}

export const RECORD = buildDecisionRecord(SAMPLE);
export const PROBE_BANDS = buildProbeBands(SAMPLE);

export const OVERVIEW = SAMPLE.overview;
export const HERO_EXCESS_PCT =
  SAMPLE.leakage.excess_segment_pct_of_booked ?? SAMPLE.leakage.excess_pct_of_booked;
