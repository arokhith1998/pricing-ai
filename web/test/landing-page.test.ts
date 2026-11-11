// @vitest-environment jsdom
//
// The landing-page rewrite (five sections, immersive, honesty-checked) must
// hold these invariants going forward:
//   1. no em dash anywhere in the visible copy (founder calls them an AI-tell)
//   2. two retired marketing claims never come back ("usage or hybrid" and
//      "system of record")
//   3. the hero's one headline number is read from the bundled sample
//      snapshot, not hand-typed, so it moves when the snapshot is
//      regenerated instead of silently going stale.
//   4. five sections, one h1, a labelled and iconed hero number, no status
//      colour on chrome, the softened headline, the no-cohort close.
//
// Written as plain React.createElement calls (no JSX) so this file can stay
// a .ts file and does not need to touch vitest.config.mts's test-file glob,
// matching the pattern in lead-form.test.ts / guidance-client.test.ts.
import { readdirSync, readFileSync } from "node:fs";
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import sampleFallback from "@/data/sample-fallback.json";
import { moneyShort } from "@/lib/format";
import { RECORD } from "@/lib/landing-sample";
import Landing, { dynamic, metadata } from "@/app/page";
import { marginViolations, stringLiterals } from "./cost-basis-guard";

afterEach(cleanup);

const leakage = sampleFallback.leakage as {
  excess_vs_segment_reference_won?: number;
  excess_vs_reference_won: number;
};
const HERO_EXCESS = leakage.excess_vs_segment_reference_won ?? leakage.excess_vs_reference_won;

describe("Landing page", () => {
  it("never uses an em dash in its copy", () => {
    const { container } = render(createElement(Landing));
    expect(container.textContent).not.toContain("—");
  });

  it("never uses the retired usage-and-hybrid fit line", () => {
    const { container } = render(createElement(Landing));
    expect(container.textContent?.toLowerCase()).not.toContain("usage and hybrid");
    expect(container.textContent?.toLowerCase()).not.toContain("usage or hybrid");
  });

  it("never says the product prices, and never claims true margin, trade or a real evidence_version", () => {
    const { container } = render(createElement(Landing));
    const t = (container.textContent ?? "").toLowerCase();
    expect(t).not.toContain("true margin");
    expect(t).not.toMatch(/prices every/);
    expect(t).not.toMatch(/trade/);
    expect(t).not.toContain("trade for terms");
    expect(t).not.toContain("evidence_version");
    expect(t).not.toContain("real engine output");
    expect(t).toContain("cost proxy, not margin");
  });

  it("metadata description says checks, not prices", () => {
    // The positioning line, no result claim, no autonomous pricing.
    expect(String(metadata.description)).toContain("We stop AI companies from losing money on heavy users.");
    expect(String(metadata.description).toLowerCase()).not.toMatch(/prices every|proven|customers/);
  });

  it("passes the ADR-006 margin guard on every landing string and on the rendered page", () => {
    const violations = marginViolations;
    // Self-check of the port against the Python rules.
    expect(violations("a cost proxy, not margin, until ERP")).toEqual([]);
    expect(violations("never labeled margin.")).toEqual([]);
    expect(violations("True margin needs ERP")).not.toEqual([]);
    expect(violations("not margin: 40%")).not.toEqual([]);
    expect(violations("not marginal")).not.toEqual([]);
    expect(violations("thin contribution margin, customer-supplied cost basis.")).toEqual([]);
    expect(violations("thin gross margin")).not.toEqual([]);
    expect(violations("contribution margin, customer-supplied")).not.toEqual([]);

    const files = [
      "src/app/page.tsx",
      "src/components/HeroHeadline.tsx",
      "src/components/DiagnosticPreview.tsx",
      "src/components/WhatYouGet.tsx",
      "src/components/TrustBoundaryStrip.tsx",
      "src/lib/audit-offer.ts",
      ...readdirSync("src/components/landing").map((f) => "src/components/landing/" + f),
    ];
    for (const f of files) {
      for (const lit of stringLiterals(readFileSync(f, "utf8"))) {
        expect(violations(lit), `${f}: ${lit}`).toEqual([]);
      }
    }
    const { container } = render(createElement(Landing));
    expect(violations(container.textContent ?? "")).toEqual([]);
  });

  it("never claims to be a system of record", () => {
    const { container } = render(createElement(Landing));
    expect(container.textContent?.toLowerCase()).not.toContain("system of record");
  });

  it("renders the sample gap straight from the bundled snapshot, below the hero", () => {
    const { container } = render(createElement(Landing));
    // Recomputed from the snapshot, so a regenerated sample-fallback.json still passes.
    const gap = container.querySelector('[data-testid="sample-gap"]');
    expect(gap?.textContent).toContain("Gap to segment win point");
    expect(gap?.textContent).toContain(moneyShort(HERO_EXCESS));
    expect(gap?.textContent).toContain("synthetic 2,000-deal book");
    expect(container.textContent).toContain("$8.9M");
    // It is not in the hero: the hero carries no figure from the sample.
    expect(container.querySelector('[data-testid="hero"]')?.textContent).not.toContain(moneyShort(HERO_EXCESS));
    expect(gap?.closest("figure")).toBeNull();
    expect(container.textContent).toContain(moneyShort(RECORD.excessDollars));
    expect(container.textContent).toContain("on this one synthetic deal");
    expect(container.textContent).not.toContain("booked above each segment");
    expect(moneyShort(HERO_EXCESS)).toBe("$8.9M");
  });

  it("states the sheet's line and audience in the hero, with no ARR number and no result claim", () => {
    const { container } = render(createElement(Landing));
    const h1 = container.querySelector("h1");
    expect(h1?.textContent).toBe("We stop AI companies from losing money on heavy users.");
    const hero = container.querySelector('[data-testid="hero"]')?.textContent ?? "";
    expect(hero).toContain("B2B and AI SaaS companies moving from flat or per-seat to usage or outcome pricing");
    expect(hero).not.toMatch(/ARR|\$\d+\s?[MK]|\d+M/);
    expect(container.textContent).not.toContain("$20M");
    expect(container.textContent?.toLowerCase()).not.toMatch(/proven|our customers|testimonial|case stud/);
    // Primary CTA is the audit; the calculator is shown as coming, never as a dead link.
    expect(container.querySelector('a[href="/audit"]')?.textContent).toContain("14-day audit");
    expect(container.querySelector('a[href="/margin-audit"]')).toBeNull();
    expect(container.querySelector('[data-testid="calculator-coming"]')?.textContent).toContain("coming");
  });

  it("walks the six bottlenecks in the sheet's order, with no figures", () => {
    const { container } = render(createElement(Landing));
    const items = [...container.querySelectorAll("[data-bottleneck]")];
    expect(items.map((i) => i.getAttribute("data-bottleneck"))).toEqual([
      "cost-floor", "packaging", "value-metric", "variance", "pilots", "bundling",
    ]);
    expect(items.map((i) => i.querySelector("h3")?.textContent)).toEqual([
      "The cost floor",
      "The packaging paradox",
      "Value metric and outcome pricing",
      "Variance and trust",
      "Pilot revenue versus true ARR",
      "Bundling",
    ]);
    for (const i of items) {
      expect((i.querySelector("p")?.textContent ?? "").replace(/B2B/g, "")).not.toMatch(/\$|\d/);
    }
  });

  it("captions the decision-record walk as the live deal-guidance product", () => {
    const { container } = render(createElement(Landing));
    const section = container.querySelector("#workflow");
    expect(section?.textContent).toContain("What the product does today");
    expect(section?.textContent).toContain("Live now: Salesforce deal guidance");
  });

  it("keeps exactly seven sections, one h1 and ordered h2s, inside a main with id=main", () => {
    const { container } = render(createElement(Landing));
    expect(container.querySelectorAll("section").length).toBe(7);
    expect(container.querySelectorAll("main > section").length).toBe(7);
    expect([...container.querySelectorAll("h2")].map((h) => h.id)).toEqual([
      "bottlenecks-h", "audit-h", "product-h", "roles-h", "boundary-h", "close-h",
    ]);
    const bands = [...container.querySelectorAll("main > section")].map((s) => s.getAttribute("data-band"));
    for (let i = 1; i < bands.length; i++) expect(bands[i]).not.toBe(bands[i - 1]);
    expect(container.querySelectorAll("h1").length).toBe(1);
    expect(container.querySelector("main")?.id).toBe("main");
  });

  it("labels the hero number with a status icon and a synthetic caption", () => {
    const { container } = render(createElement(Landing));
    const pills = [...container.querySelectorAll('[data-status="leak"]')].map((p) => p.textContent);
    expect(pills.some((t) => t?.includes("Gap to segment win point"))).toBe(true);
    const pill = container.querySelector('[data-status="leak"]');
    expect(pill?.querySelector("svg")).toBeTruthy();
    expect(container.textContent?.toLowerCase()).toContain("synthetic sample deal");
  });

  it("has no coral headline, glow, tilt, amber chrome or 100svh hero", () => {
    const { container } = render(createElement(Landing));
    const h1 = container.querySelector("h1");
    expect(h1?.outerHTML).not.toContain("coral");
    expect(h1?.outerHTML).not.toContain("pk-headline-accent");
    for (const bad of ["100svh", "pk-upside", "pk-card-3d", "amber", "rounded-full bg-coral"]) {
      expect(container.innerHTML).not.toContain(bad);
    }
    // The only coral on the page: the leak pill and the hero number.
    expect(container.querySelectorAll('[class*="coral"]').length).toBe(4);
  });

  it("uses the sheet headline, the synthetic-book wording and the no-cohort close", () => {
    const { container } = render(createElement(Landing));
    const text = container.textContent ?? "";
    expect(text).not.toContain("wins you nothing");
    expect(text).toContain("We stop AI companies from losing money on heavy users.");
    expect(text).not.toContain("Stop giving away price that has stopped winning deals.");
    expect(text.toLowerCase()).not.toContain("cohort");
    expect(text).toContain("In this synthetic book, win rate stops improving past the win point.");
    expect(text).not.toContain("buy fewer wins, not more");
  });

  it("shows the synthetic deal tag and never an account name", () => {
    const { container } = render(createElement(Landing));
    expect(container.textContent).toContain("Synthetic sample deal. Figures from the bundled synthetic snapshot.");
    const deals = sampleFallback.top_leak_deals as { resolved_account_name: string }[];
    for (const d of deals) expect(container.textContent).not.toContain(d.resolved_account_name);
  });

  it("stays static and exports page metadata through pageMetadata()", () => {
    expect(dynamic).toBe("force-static");
    expect(String(metadata.title)).not.toContain("Pricekeel");
    expect(metadata.alternates?.canonical).toBe("/");
    const d = String(metadata.description);
    expect(d.length).toBeGreaterThanOrEqual(70);
    expect(d.length).toBeLessThanOrEqual(160);
    expect(metadata.openGraph?.images).toBeTruthy();
  });
});
