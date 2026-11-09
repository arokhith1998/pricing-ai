// @vitest-environment jsdom
//
// PK-14 (follow-up to the PK-11 audit): copy that asserted a fact instead of
// computing it. Pins three claims by rendering the real components:
//   1. Comparables caption says "won and lost" only when the rendered rows
//      hold both outcomes, otherwise names what they hold.
//   2. The /diagnostic win-rate subtitle is derived from the shape of
//      win_rate_by_band and never asserts a shape the bands do not show.
//   3. The expected-value headline says "less" (never "more") when
//      rec.uplift is negative, matching the coral tile accent.
// Every figure asserted here comes from a fixture field, so a number that
// was computed in the UI or invented would not match. No JSX, so this stays
// a .ts file (same pattern as guidance-client.test.ts).
import { createElement } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import GuidanceClient from "@/components/GuidanceClient";
import type { ComparableDeal, Deal, Diagnostic, Recommendation } from "@/lib/api";
import sampleFallback from "@/data/sample-fallback.json";

const EM_DASH = "—";

let bandFixture: { win_rate: number; deals?: number }[] = [];
let thresholdFixture = 0.2;

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getDemo: vi.fn(async () => {
      const base = sampleFallback as unknown as Diagnostic;
      return {
        ...base,
        win_rate_by_band: bandFixture.map((b, i) => ({
          discount_band: `${i * 5}-${i * 5 + 5}%`,
          deals: b.deals ?? 50,
          won: Math.round((b.deals ?? 50) * b.win_rate),
          avg_discount: i * 0.05 + 0.025,
          win_rate: b.win_rate,
        })),
        leakage: { ...base.leakage, reference_threshold: thresholdFixture },
      } as Diagnostic;
    }),
  };
});

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

function comp(id: string, is_won: boolean): ComparableDeal {
  return {
    opportunity_id: id,
    resolved_account_name: `Acct ${id}`,
    segment: "Enterprise",
    list_acv: 400_000,
    discount_pct: 0.1,
    is_won,
  };
}

function makeRec(overrides: Partial<Recommendation>): Recommendation {
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

async function renderRec(rec: Recommendation) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(rec), { status: 200 })),
  );
  render(createElement(GuidanceClient, { deals: [deal] }));
  await waitFor(() => screen.getByText(/model suggests/i));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("PK-14 criterion 1: comparables outcome label", () => {
  const caption = () => screen.getByText(/The closest closed deals by segment/).textContent ?? "";

  it("says 'won and lost' when the rendered set holds both outcomes", async () => {
    await renderRec(makeRec({ comparables: [comp("a", true), comp("b", false)] }));
    expect(caption()).toContain("won and lost");
  });

  it("says 'all won' and not 'won and lost' when every rendered row is won", async () => {
    await renderRec(makeRec({ comparables: [comp("a", true), comp("b", true)] }));
    expect(caption()).toContain("all won");
    expect(caption()).not.toContain("won and lost");
  });

  it("says 'all lost' and not 'won and lost' when every rendered row is lost", async () => {
    await renderRec(makeRec({ comparables: [comp("a", false), comp("b", false)] }));
    expect(caption()).toContain("all lost");
    expect(caption()).not.toContain("won and lost");
  });

  it("makes no outcome claim when there are no rows", async () => {
    await renderRec(makeRec({ comparables: [] }));
    expect(caption()).not.toMatch(/won|lost/);
  });
});

describe("PK-14 criterion 2: win-rate subtitle follows the band shape", () => {
  async function subtitle(rates: number[], threshold = 0.2, deals?: number[]) {
    bandFixture = rates.map((win_rate, i) => ({ win_rate, deals: deals?.[i] }));
    thresholdFixture = threshold;
    const { renderToStaticMarkup } = await import("react-dom/server");
    const { default: DiagnosticPage } = await import("@/app/diagnostic/page");
    document.body.innerHTML = renderToStaticMarkup(await DiagnosticPage());
    const h2 = Array.from(document.body.querySelectorAll("h2")).find(
      (h) => h.textContent === "Win rate vs discount",
    );
    expect(h2).toBeDefined();
    return h2!.nextElementSibling!.textContent ?? "";
  }

  it("monotone bands: says it keeps climbing, never 'flattens'", async () => {
    const s = await subtitle([0.3, 0.45, 0.6, 0.75]);
    expect(s).toContain("keeps climbing");
    expect(s).not.toMatch(/flattens|both up and down/);
  });

  it("climb then plateau: says 'climbs with discount, then flattens' and names the API win point", async () => {
    const s = await subtitle([0.3, 0.5, 0.6, 0.605, 0.61], 0.37);
    expect(s).toContain("climbs with discount, then flattens");
    expect(s).toContain("about 37%");
  });

  it("non-monotone bands (rise, drop): makes no climb-then-flatten claim", async () => {
    const s = await subtitle([0.3, 0.6, 0.4, 0.5]);
    expect(s).toContain("does not follow a clean climb-then-flatten pattern");
    expect(s).not.toMatch(/keeps climbing|then flattens/);
  });

  it("falling-only bands: does not claim it moves up", async () => {
    const s = await subtitle([0.6, 0.5, 0.4]);
    expect(s).not.toMatch(/climbs|keeps climbing|both up and down/);
  });

  it("a rise after a plateau is not described as flattening", async () => {
    const s = await subtitle([0.2, 0.4, 0.4, 0.6]);
    expect(s).not.toMatch(/then flattens/);
  });

  it("flat bands: says roughly flat; slow drift beyond tolerance does not", async () => {
    expect(await subtitle([0.4, 0.41, 0.4, 0.405])).toContain("roughly flat");
    expect(await subtitle([0.4, 0.42, 0.44, 0.46])).not.toContain("roughly flat");
  });

  it("zero-deal bands are ignored; too few populated bands describes no shape", async () => {
    const s = await subtitle([0.3, 0.5, 0.6, 0.7], 0.2, [50, 0, 0, 50]);
    expect(s).toContain("Not enough discount bands");
    expect(s).not.toMatch(/climbs|flattens|flat/);
  });

  it("never contains an em dash", async () => {
    for (const rates of [[0.3, 0.45, 0.6], [0.3, 0.5, 0.5], [0.5, 0.3, 0.5], [0.4, 0.4, 0.4], [0.4]]) {
      expect(await subtitle(rates)).not.toContain(EM_DASH);
    }
  });
});

describe("PK-14 criterion 3: expected-value headline vs uplift sign", () => {
  const headline = () => screen.getByText(/model suggests/i).closest("p")!.textContent ?? "";

  it("positive uplift: 'more in expected value' with the API figure, tile not coral", async () => {
    await renderRec(makeRec({ uplift: 67_006 }));
    expect(headline()).toContain("$67,006 more in expected value");
    expect(headline()).not.toContain("less in expected value");
  });

  it("negative uplift: 'less in expected value', the unsigned API figure, coral tile", async () => {
    await renderRec(makeRec({ uplift: -12_345 }));
    const h = headline();
    expect(h).toContain("$12,345 less in expected value");
    expect(h).not.toContain("more in expected value");
    // Tile: coral accent for the loss, same figure as the headline.
    const figures = screen.getAllByText(/\$12,345/);
    expect(figures.some((el) => el.className.includes("text-coral"))).toBe(true);
    expect(screen.getByText("Expected value gain")).toBeTruthy();
  });

  it("raising or holding the discount makes no 'more/less in expected value' claim", async () => {
    await renderRec(makeRec({ recommended_discount: 0.14, uplift: -500 }));
    expect(headline()).not.toMatch(/(more|less) in expected value/);
  });

  it("headline copy has no em dash", async () => {
    await renderRec(makeRec({ uplift: -12_345 }));
    expect(headline()).not.toContain(EM_DASH);
  });
});
