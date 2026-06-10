// Public leakage math — a faithful TypeScript mirror of the real diagnostic.
//
// The authoritative definitions live in pricing/metrics.py (leakage lenses)
// and pricing/schema.py (DEFAULT_POLICY_THRESHOLD). This file reproduces ONLY
// what is honestly computable from aggregate inputs, so the public calculator
// can never claim more than the math supports:
//
//   Lens 1  Gross discount $ (list - booked) ......... computed exactly here.
//   Lens 2  Off-policy $ (discount above the 0.15 line) computed as an
//           AGGREGATE APPROXIMATION from the average discount. The real
//           diagnostic clips each deal individually, so the true figure is
//           usually LARGER than this blended-average estimate (a spread of
//           deals puts more volume past the line than the mean reveals).
//   Lens 3  Excess-vs-reference $ — deliberately NOT estimated here. It needs
//           per-deal win/loss outcomes and a bootstrapped reference discount
//           (metrics.reference_discount); aggregates cannot produce it without
//           inventing a recovery rate. That number comes from the real CSV.

// Mirror of pricing/schema.py: DEFAULT_POLICY_THRESHOLD. Discount above this is
// "off-policy" and would require deal-desk approval. 15% is a common line.
export const POLICY_THRESHOLD = 0.15;

export type LeakageInputs = {
  /** Annualized booked value, post-discount (the ARR proxy). */
  bookedAcv: number;
  /** Average discount as a fraction in [0, 1), e.g. 0.18 for 18%. */
  avgDiscount: number;
  /** Optional deal count, for per-deal context only. */
  deals?: number;
};

export type LeakageResult = {
  bookedAcv: number;
  /** Implied list value = booked / (1 - avgDiscount). */
  listAcv: number;
  /** booked / list — the diagnostic's price-realization figure. */
  priceRealization: number;
  /** Lens 1: total discount given back, list - booked. */
  grossDiscount: number;
  grossPctOfBooked: number;
  /** Lens 2 (aggregate approx): (avgDiscount - 0.15)+ x list. */
  abovePolicy: number;
  abovePolicyPctOfBooked: number;
  /** Gross discount per deal, when a deal count is supplied. */
  perDealGross: number | null;
  policyThreshold: number;
};

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));

export function computeLeakage({ bookedAcv, avgDiscount, deals }: LeakageInputs): LeakageResult {
  const booked = Math.max(0, bookedAcv);
  // Cap discount short of 100% so the implied-list division stays finite.
  const d = clamp(avgDiscount, 0, 0.95);

  const listAcv = booked > 0 ? booked / (1 - d) : 0;
  const grossDiscount = Math.max(0, listAcv - booked);
  const overPolicy = Math.max(0, d - POLICY_THRESHOLD);
  const abovePolicy = overPolicy * listAcv;

  return {
    bookedAcv: booked,
    listAcv,
    priceRealization: listAcv > 0 ? booked / listAcv : 0,
    grossDiscount,
    grossPctOfBooked: booked > 0 ? grossDiscount / booked : 0,
    abovePolicy,
    abovePolicyPctOfBooked: booked > 0 ? abovePolicy / booked : 0,
    perDealGross: deals && deals > 0 ? grossDiscount / deals : null,
    policyThreshold: POLICY_THRESHOLD,
  };
}
