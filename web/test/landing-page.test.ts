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

  it("never claims usage-or-hybrid fit (dropped from the ICP line)", () => {
    const { container } = render(createElement(Landing));
    expect(container.textContent?.toLowerCase()).not.toContain("usage or hybrid");
    expect(container.textContent?.toLowerCase()).not.toContain("usage and hybrid");
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
    expect(String(metadata.description)).toContain("checks every discount exception");
    expect(String(metadata.description).toLowerCase()).not.toMatch(/usage (and|or) hybrid|prices every/);
  });

  it("passes the ADR-006 margin guard on every landing string and on the rendered page", () => {
    // Ported from pricing/cost_basis.py (keep in sync with its allowlist
    // comment): exactly four negations, whole-phrase only, never followed by a
    // figure; any other "margin" next to a CRM cost proxy is a violation.
    const ALLOWED = ["not margin", "never labeled margin", "not bookable margin", "not cost-based margin"];
    const LEAD_IN =
      String.raw`(?:\.\.\.|\u2026|[:,(\u2013\u2014])\s*[-\u2212\u2013]?\s*` +
      String.raw`(?:(?:about|roughly|around|nearly|over|under|approximately|circa|i\.e\.|e\.g\.)\s*,?\s*)?[\d$%]`;
    const allowedRe = new RegExp(
      String.raw`(?<![\w-])(?:` +
        ALLOWED.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") +
        String.raw`)(?=\s*$|\s*[^\w\s\-])(?!\s*` +
        LEAD_IN +
        ")",
      "gi",
    );
    const violations = (text: string): string[] => {
      const covered = [...text.matchAll(allowedRe)].map((m) => [m.index!, m.index! + m[0].length]);
      return [...text.matchAll(/margin/gi)]
        .filter((m) => !covered.some(([a, b]) => a <= m.index! && m.index! < b))
        .map((m) => text.slice(Math.max(0, m.index! - 30), m.index! + 22));
    };
    // Self-check of the port against the Python rules.
    expect(violations("a cost proxy, not margin, until ERP")).toEqual([]);
    expect(violations("never labeled margin.")).toEqual([]);
    expect(violations("True margin needs ERP")).not.toEqual([]);
    expect(violations("not margin: 40%")).not.toEqual([]);
    expect(violations("not marginal")).not.toEqual([]);

    const files = [
      "src/app/page.tsx",
      "src/components/HeroHeadline.tsx",
      "src/components/DiagnosticPreview.tsx",
      "src/components/WhatYouGet.tsx",
      "src/components/TrustBoundaryStrip.tsx",
      ...readdirSync("src/components/landing").map((f) => "src/components/landing/" + f),
    ];
    const literalRe = /"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`/g;
    for (const f of files) {
      for (const lit of readFileSync(f, "utf8").match(literalRe) ?? []) {
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

  it("renders the hero number straight from the bundled sample snapshot", () => {
    const { container } = render(createElement(Landing));
    // Asserts the RENDERED text. Recomputed from the snapshot, so a regenerated
    // sample-fallback.json still passes. Today: 8,946,770 shown as $8.9M.
    const gap = container.querySelector('[data-testid="hero-gap"]');
    expect(gap?.textContent).toContain("Gap to segment win point");
    expect(gap?.textContent).toContain(moneyShort(HERO_EXCESS));
    expect(gap?.textContent).toContain("synthetic 2,000-deal book");
    expect(container.textContent).toContain("$8.9M");
    // The record shows this one deal's own excess, never the book total.
    expect(container.querySelector('[data-testid="hero-gap"]')?.closest("figure")).toBeNull();
    expect(container.textContent).toContain(moneyShort(RECORD.excessDollars));
    expect(container.textContent).toContain("on this one synthetic deal");
    expect(container.textContent).not.toContain("booked above each segment");
    expect(moneyShort(HERO_EXCESS)).toBe("$8.9M");
  });

  it("keeps exactly five sections and one h1, inside a main with id=main", () => {
    const { container } = render(createElement(Landing));
    expect(container.querySelectorAll("section").length).toBe(5);
    expect(container.querySelectorAll("main > section").length).toBe(5);
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

  it("uses the softened headline, the synthetic-book wording and the no-cohort close", () => {
    const { container } = render(createElement(Landing));
    const text = container.textContent ?? "";
    expect(text).not.toContain("wins you nothing");
    expect(text).toContain("Stop giving away price that has stopped winning deals.");
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
