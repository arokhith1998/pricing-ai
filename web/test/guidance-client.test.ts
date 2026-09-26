// @vitest-environment jsdom
//
// PK-11: the headline sentence on the guidance page hardcoded "barely
// moving the odds of winning" for every discount-lowering recommendation
// without checking win_prob_at_current / win_prob_at_rec, which are
// rendered in the stat tile directly below it. Beyond WIN_PROB_BARELY_
// THRESHOLD_PTS (a 2-point move) the sentence must name the actual change
// instead of calling it negligible. A second bug let the headline round the
// raw difference while the stat tile rounded each probability independently,
// so the two could disagree by a point. These tests render the real
// component (not a pure-function extraction of the copy logic) because the
// acceptance bar is "the sentence must never contradict the stat tile below
// it" -- that is only actually checked by asserting on both together.
//
// Written as plain React.createElement calls (no JSX) so this file can
// stay a .ts file and does not need to touch vitest.config.mts's test-file
// glob, matching the pattern in lead-form.test.ts.
import { createElement } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import GuidanceClient, { WIN_PROB_BARELY_THRESHOLD_PTS } from "@/components/GuidanceClient";
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

  it(`calls it 'barely moving the odds' only when the change is at or below the threshold (${WIN_PROB_BARELY_THRESHOLD_PTS} points)`, async () => {
    const winProbAtCurrent = 0.3;
    const winProbAtRec = winProbAtCurrent - WIN_PROB_BARELY_THRESHOLD_PTS / 100; // exactly at the threshold
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: winProbAtCurrent,
      win_prob_at_rec: winProbAtRec,
    });
    await renderWithRecommendation(rec);

    screen.getByText(/barely moving the odds of winning/i);
    expect(screen.queryByText(/point drop in win probability/i)).toBeNull();

    // Consistency check against the stat tile: both numbers it renders
    // must be the exact values the headline's claim was checked against.
    screen.getByText(/28%/);
    screen.getByText(/was 30% at the current discount/i);
  });

  it("computes the headline delta from the same rounded percentages the stat tile shows, not the raw difference (0.344 -> 0.318)", async () => {
    // Pre-fix, Math.round((0.318 - 0.344) * 100) = -3, so the headline said
    // "3 point drop" while the tile (independently rounded) showed 34% -> 32%,
    // a 2-point move. Deriving the headline from the same rounded integers
    // the tile renders makes the two agree by construction.
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: 0.344,
      win_prob_at_rec: 0.318,
    });
    await renderWithRecommendation(rec);

    screen.getByText(/32%/);
    screen.getByText(/was 34% at the current discount/i);
    screen.getByText(/barely moving the odds of winning/i);
    expect(screen.queryByText(/point drop in win probability/i)).toBeNull();
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

  it("names the actual rise in win probability when a lowering recommendation still improves the odds", async () => {
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: 0.3,
      win_prob_at_rec: 0.37, // discount goes down, win probability goes up
    });
    await renderWithRecommendation(rec);

    screen.getByText(/lifts the odds of winning by 7 points/i);
    expect(screen.queryByText(/barely moving the odds of winning/i)).toBeNull();
    expect(screen.queryByText(/point drop in win probability/i)).toBeNull();

    // The stat tile the headline must not contradict.
    screen.getByText(/37%/);
    screen.getByText(/was 30% at the current discount/i);
  });

  it("falls back to claim-free wording instead of guessing when the win-probability delta is not finite", async () => {
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: 0.3,
    });
    // Simulates a malformed API response missing win_prob_at_rec. Built by
    // hand rather than via JSON.stringify(rec) with win_prob_at_rec set to
    // NaN: JSON has no NaN literal, so JSON.stringify silently coerces NaN
    // (and Infinity) to null, which then coerces to 0 in arithmetic instead
    // of staying non-finite, defeating the point of this test.
    const payload: Record<string, unknown> = { ...rec };
    delete payload.win_prob_at_rec;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 })),
    );
    render(createElement(GuidanceClient, { deals: [deal] }));
    await waitFor(() => screen.getByText(/model suggests/i));

    screen.getByText(/that changes the discount, for about/i);
    expect(screen.queryByText(/barely moving the odds of winning/i)).toBeNull();
    expect(screen.queryByText(/point drop in win probability/i)).toBeNull();
    expect(screen.queryByText(/lifts the odds of winning/i)).toBeNull();
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

  // PK-14: the accent on the Expected value gain tile already branches on
  // rec.uplift's sign (coral below zero), but the headline sentence said
  // "more in expected value" unconditionally, contradicting a coral tile
  // sitting right below a "more" claim.
  it("says 'less', not 'more', in expected value when uplift is negative", async () => {
    const rec = makeRecommendation({
      current_discount: 0.14,
      recommended_discount: 0.04,
      win_prob_at_current: 0.3,
      win_prob_at_rec: 0.29,
      uplift: -12_500,
    });
    await renderWithRecommendation(rec);

    screen.getByText(/\$12,500/);
    screen.getByText(/less in expected value/i);
    expect(screen.queryByText(/more in expected value/i)).toBeNull();
  });
});

describe("GuidanceClient comparables outcome label", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  function comparable(overrides: Partial<Recommendation["comparables"][number]>) {
    return {
      opportunity_id: "cmp-1",
      resolved_account_name: "Comparable Co",
      segment: "Enterprise",
      list_acv: 300_000,
      discount_pct: 0.1,
      is_won: true,
      ...overrides,
    };
  }

  it("says 'won and lost' only when comparables actually contain both outcomes", async () => {
    const rec = makeRecommendation({
      comparables: [comparable({ opportunity_id: "cmp-1", is_won: true }), comparable({ opportunity_id: "cmp-2", is_won: false })],
    });
    await renderWithRecommendation(rec);

    screen.getByText(/won and lost/i);
  });

  it("says 'all won' when every comparable won, not 'won and lost'", async () => {
    const rec = makeRecommendation({
      comparables: [comparable({ opportunity_id: "cmp-1", is_won: true }), comparable({ opportunity_id: "cmp-2", is_won: true })],
    });
    await renderWithRecommendation(rec);

    screen.getByText(/all won/i);
    expect(screen.queryByText(/won and lost/i)).toBeNull();
  });

  it("says 'all lost' when every comparable lost, not 'won and lost'", async () => {
    const rec = makeRecommendation({
      comparables: [comparable({ opportunity_id: "cmp-1", is_won: false })],
    });
    await renderWithRecommendation(rec);

    screen.getByText(/all lost/i);
    expect(screen.queryByText(/won and lost/i)).toBeNull();
  });
});
