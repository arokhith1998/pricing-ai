// @vitest-environment jsdom
//
// PK-11: the headline sentence on the guidance page hardcoded "barely
// moving the odds of winning" for every discount-lowering recommendation
// without checking win_prob_at_current / win_prob_at_rec, which are
// rendered in the stat tile directly below it. On about 2% of deals the
// odds move by more than a rounding error and the sentence contradicted
// the number on screen. These tests render the real component (not a
// pure-function extraction of the copy logic) because the acceptance bar
// is "the sentence must never contradict the stat tile below it" -- that
// is only actually checked by asserting on both together.
//
// Written as plain React.createElement calls (no JSX) so this file can
// stay a .ts file and does not need to touch vitest.config.mts's test-file
// glob, matching the pattern in lead-form.test.ts.
import { createElement } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import GuidanceClient from "@/components/GuidanceClient";
import type { Deal, Recommendation } from "@/lib/api";

const deal: Deal = {
  opportunity_id: "opp-1",
  resolved_account_name: "Juniper Networks",
  segment: "Enterprise",
  industry: "Networking",
  product_tier: "Platform",
  list_acv: 500_000,
  discount_pct: 0.14,
  competitor_present: false,
  is_quarter_end: false,
};

function makeRecommendation(overrides: Partial<Recommendation>): Recommendation {
  return {
    opportunity_id: "opp-1",
    account: "Juniper Networks",
    segment: "Enterprise",
    list_acv: 500_000,
    current_discount: 0.14,
    recommended_discount: 0.04,
    win_prob_at_current: 0.3,
    win_prob_at_rec: 0.29,
    expected_acv_at_current: 400_000,
    expected_acv_at_rec: 467_006,
    uplift: 67_006,
    top_factors: [],
    comparables: [],
    band_context: {
      segment: "Enterprise",
      cohort_deals: 40,
      bands: [],
      current_band: "10-15%",
      recommended_band: "0-5%",
    },
    confidence: { auc: 0.78, mean_pred: 0.31, base_rate: 0.3, n_train: 620 },
    curve: [],
    ...overrides,
  };
}

async function renderWithRecommendation(rec: Recommendation) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(rec), { status: 200 })),
  );
  render(createElement(GuidanceClient, { deals: [deal] }));
  // The headline only appears once the fetch resolves.
  await waitFor(() => screen.getByText(/model suggests/i));
}

describe("GuidanceClient headline vs. the win-probability stat tile", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("calls it 'barely moving the odds' only when the change is at or below the threshold (1 point)", async () => {
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: 0.3,
      win_prob_at_rec: 0.29, // -1 point, within WIN_PROB_BARELY_THRESHOLD_PTS
    });
    await renderWithRecommendation(rec);

    screen.getByText(/barely moving the odds of winning/i);
    expect(screen.queryByText(/point drop in win probability/i)).toBeNull();

    // Consistency check against the stat tile: both numbers it renders
    // must be the exact values the headline's claim was checked against.
    screen.getByText(/29%/);
    screen.getByText(/was 30% at the current discount/i);
  });

  it("states the actual drop instead of 'barely' once win probability falls more than the threshold", async () => {
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: 0.4,
      win_prob_at_rec: 0.33, // -7 points, past WIN_PROB_BARELY_THRESHOLD_PTS
    });
    await renderWithRecommendation(rec);

    screen.getByText(/7 point drop in win probability/i);
    expect(screen.queryByText(/barely moving the odds of winning/i)).toBeNull();

    // The stat tile the headline must not contradict.
    screen.getByText(/33%/);
    screen.getByText(/was 40% at the current discount/i);
  });

  it("does not claim a discount was lowered, or say anything about win odds, when the recommendation raises it", async () => {
    const rec = makeRecommendation({
      current_discount: 0.1,
      recommended_discount: 0.18,
      win_prob_at_current: 0.55,
      win_prob_at_rec: 0.4, // a real drop, but this is not the "lower" branch
    });
    await renderWithRecommendation(rec);

    screen.getByText(/to maximize expected value/i);
    expect(screen.queryByText(/lowering the discount/i)).toBeNull();
    expect(screen.queryByText(/barely moving the odds of winning/i)).toBeNull();
    expect(screen.queryByText(/point drop in win probability/i)).toBeNull();
  });
});
