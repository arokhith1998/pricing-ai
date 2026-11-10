// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import sampleFallback from "@/data/sample-fallback.json";
import type { LeakDeal } from "@/lib/api";
import DecisionWalk, { WalkView, buildSteps } from "@/components/landing/DecisionWalk";
import DiagnosticPreview from "@/components/DiagnosticPreview";
import {
  PROBE_BANDS,
  RECORD,
  SAMPLE,
  bandForDiscount,
  buildDecisionRecord,
  peakBandLabel,
  selectSampleDeal,
} from "@/lib/landing-sample";
import { pct } from "@/lib/format";

afterEach(cleanup);

const deal = (id: string, excess: number): LeakDeal =>
  ({ opportunity_id: id, excess_discount_dollars: excess }) as LeakDeal;

describe("deal selection rule", () => {
  it("takes the largest excess discount dollars", () => {
    expect(selectSampleDeal([deal("B", 1), deal("A", 5), deal("C", 3)]).opportunity_id).toBe("A");
  });
  it("breaks ties by the lower opportunity id, whatever the order", () => {
    expect(selectSampleDeal([deal("OPP-2", 5), deal("OPP-1", 5)]).opportunity_id).toBe("OPP-1");
    expect(selectSampleDeal([deal("OPP-1", 5), deal("OPP-2", 5)]).opportunity_id).toBe("OPP-1");
  });
  it("is stable on the bundled snapshot and never exposes the account name", () => {
    expect(RECORD.opportunityId).toBe("OPP-00280");
    expect(JSON.stringify(RECORD)).not.toContain("Lattice");
    expect(buildDecisionRecord(SAMPLE)).toEqual(RECORD);
  });
  it("maps a discount to its band and finds the win point from the data", () => {
    const labels = PROBE_BANDS.map((b) => b.label);
    expect(bandForDiscount(0.399837, labels)).toBe("25%+");
    expect(bandForDiscount(0.05, labels)).toBe("5-10%");
    expect(bandForDiscount(0.0, labels)).toBe("0-5%");
    expect(peakBandLabel(PROBE_BANDS)).toBe(SAMPLE.reference_discount.peak_band);
  });
});

describe("walk without the arming effect", () => {
  const steps = buildSteps(RECORD);
  const unarmed = () =>
    renderToStaticMarkup(<WalkView steps={steps} record={RECORD} armed={false} />);

  it("renders four steps, stacked and fully visible, each with its own panel", () => {
    const html = unarmed();
    for (const name of ["Request", "Evidence", "Decision", "Outcome"]) expect(html).toContain(name);
    expect(html).toContain('data-armed="false"');
    expect(html).not.toMatch(/opacity:\s*0/);
    expect(html).not.toContain("opacity-");
    expect(html).not.toContain("sticky");
    expect((html.match(/data-step=/g) ?? []).length).toBe(4);
    expect(html).toContain(RECORD.opportunityId);
    expect(html.toLowerCase()).not.toContain("fingerprint");
    expect(html).not.toContain("evidence_version");
    expect(html).not.toMatch(/trade/i);
    expect(html).toContain("all segments");
    expect(html).toContain("Log row");
    expect(html).toContain("Won in the synthetic book");
  });
  it("the real component's server render is never armed", () => {
    const html = renderToStaticMarkup(<DecisionWalk record={RECORD} />);
    expect(html).toContain('data-armed="false"');
    expect((html.match(/data-step=/g) ?? []).length).toBe(4);
  });
  it("decision step shows a human choosing and never says the product sets or approves a price", () => {
    const html = unarmed();
    expect(html).toContain("Chosen by a person");
    expect(html).toContain("A person chooses.");
    expect(html.toLowerCase()).not.toMatch(
      /(pricekeel|the product|the engine|we) (sets|approves|decides|picks)/,
    );
    expect(html.toLowerCase()).not.toContain("auto-approve");
    expect(html).not.toContain("—");
  });
  it("outcome says it is what the synthetic book recorded", () => {
    expect(unarmed()).toContain("What the synthetic book recorded.");
  });
  it("armed form shows one panel for the active step", () => {
    const html = renderToStaticMarkup(<WalkView steps={steps} record={RECORD} armed active={2} />);
    expect(html).toContain('data-armed="true"');
    expect((html.match(/Log row/g) ?? []).length).toBe(1);
  });
});

describe("band probe", () => {
  const data = {
    opportunities: 2000,
    bookedAcvWon: 1,
    priceRealizationWon: 0.8,
    avgDiscountWon: 0.1,
    winRate: 0.6,
    bands: PROBE_BANDS,
    peakBand: peakBandLabel(PROBE_BANDS),
    initialBand: "25%+",
  };
  it("reads win_rate_by_band and band_win_rate_ci", () => {
    for (const b of PROBE_BANDS) {
      const row = SAMPLE.win_rate_by_band.find((r) => r.discount_band === b.label)!;
      const ci = SAMPLE.reference_discount.band_win_rate_ci[b.label];
      expect(b.winRate).toBe(row.win_rate);
      expect([b.ciLow, b.ciHigh]).toEqual([ci[1], ci[2]]);
    }
    expect(PROBE_BANDS.length).toBe(sampleFallback.win_rate_by_band.length);
  });
  it("shows the selected band's interval and changes on selection", () => {
    render(<DiagnosticPreview data={data} />);
    const last = PROBE_BANDS[5];
    expect(screen.getByText(`${pct(last.ciLow)} to ${pct(last.ciHigh)}`)).toBeTruthy();
    fireEvent.click(screen.getByLabelText("5-10%"));
    const peak = PROBE_BANDS[1];
    expect(screen.getByText(`${pct(peak.ciLow)} to ${pct(peak.ciHigh)}`)).toBeTruthy();
    expect(screen.getByText(/the win point: the band with the highest win rate/)).toBeTruthy();
  });
  it("says it is a lookup, not a forecast, and calls no network", () => {
    const calls: unknown[] = [];
    const orig = globalThis.fetch;
    globalThis.fetch = ((...a: unknown[]) => {
      calls.push(a);
      return Promise.reject(new Error("no network"));
    }) as typeof fetch;
    try {
      render(<DiagnosticPreview data={data} />);
      fireEvent.click(screen.getByLabelText("0-5%"));
    } finally {
      globalThis.fetch = orig;
    }
    expect(calls.length).toBe(0);
    expect(screen.getByText(/not a forecast/)).toBeTruthy();
  });
});
