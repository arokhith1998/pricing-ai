// @vitest-environment jsdom
//
// F15 and ADR-008: the landing page is minimal and follows the two research
// sheet tabs only. In order: the sheet's line as the h1, one audience
// sentence, the six bottlenecks as one tight list, the offer in three lines
// with one call to action to /audit. Nothing else. This file pins that
// structure, keeps the ADR-006 guard over every string, and bans the phrases
// that were removed.
//
// Plain React.createElement (no JSX) so this stays a .ts file.
import { readdirSync, readFileSync } from "node:fs";
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import Landing, { dynamic, metadata } from "@/app/page";
import { BOOKING_LABEL, BOOKING_URL } from "@/lib/site-nav";
import { marginViolations, stringLiterals } from "./cost-basis-guard";

afterEach(cleanup);

const text = () => render(createElement(Landing)).container.textContent ?? "";

describe("Landing page", () => {
  it("has the sheet's line as the one h1, then the audience sentence", () => {
    const { container } = render(createElement(Landing));
    const h1s = container.querySelectorAll("h1");
    expect(h1s).toHaveLength(1);
    expect(h1s[0].textContent).toBe("We stop AI companies from losing money on heavy users.");
    expect(container.querySelector('[data-testid="audience"]')?.textContent).toBe(
      "For B2B and AI software companies moving from flat or per-seat to usage or outcome pricing.",
    );
    // The h1 is the first thing in the main, and the audience sentence follows it.
    // The hero then carries the booking button and one quiet link to /audit.
    const hero = container.querySelector("main > section");
    expect(hero?.textContent).toBe(
      "We stop AI companies from losing money on heavy users.For B2B and AI software companies moving from flat or per-seat to usage or outcome pricing.Book a 20-minute callSee the 14-day audit",
    );
  });

  it("lists the six bottlenecks in the sheet's order, one line each, no figures", () => {
    const { container } = render(createElement(Landing));
    const items = [...container.querySelectorAll("[data-bottleneck]")];
    expect(items.map((i) => i.getAttribute("data-bottleneck"))).toEqual([
      "cost-floor", "packaging", "value-metric", "variance", "pilots", "bundling",
    ]);
    expect(items.map((i) => i.querySelector("span")?.textContent)).toEqual([
      "The cost floor.",
      "The packaging paradox.",
      "Value metric and outcome pricing.",
      "Variance and trust.",
      "Pilot revenue versus true ARR.",
      "Bundling.",
    ]);
    for (const i of items) {
      expect((i.textContent ?? "").replace(/B2B/g, "")).not.toMatch(/\$|\d/);
      expect(i.querySelectorAll("p, li, br")).toHaveLength(0);
    }
  });

  it("states the offer in three lines, with no validated-intake wording", () => {
    const { container } = render(createElement(Landing));
    const lines = [...container.querySelectorAll('[data-testid="offer"] > li')].map((l) => l.textContent);
    expect(lines).toEqual([
      "A done-for-you audit of your billing and cost exports: which customers and plans cost more to serve than they pay, on contribution margin, customer-supplied cost basis, and a packaging structure for you to decide on.",
      "14 days from the day your files arrive and check out.",
      "$7,500 fixed, paid upfront.",
    ]);
    expect(text().toLowerCase()).not.toContain("validated intake");
  });

  it("has one booking button using the constant, and a quiet link to /audit", () => {
    const { container } = render(createElement(Landing));
    const links = [...container.querySelectorAll("main a")];
    expect(links.map((l) => [l.textContent, l.getAttribute("href")])).toEqual([
      [BOOKING_LABEL, BOOKING_URL],
      ["See the 14-day audit", "/audit"],
    ]);
    expect(links[0].className).toContain("bg-teal");
    expect(links[1].className).not.toContain("bg-teal");
  });

  it("has exactly three sections and ordered h2s, nothing else", () => {
    const { container } = render(createElement(Landing));
    expect(container.querySelectorAll("main > section")).toHaveLength(3);
    expect(container.querySelectorAll("section")).toHaveLength(3);
    expect([...container.querySelectorAll("h2")].map((h) => h.id)).toEqual(["bottlenecks-h", "offer-h"]);
    expect(container.querySelector("main")?.id).toBe("main");
    const bands = [...container.querySelectorAll("main > section")].map((s) => s.getAttribute("data-band"));
    for (let i = 1; i < bands.length; i++) expect(bands[i]).not.toBe(bands[i - 1]);
    for (const tag of ["table", "svg", "figure", "img", "button", "input", "form"]) {
      expect(container.querySelector(tag), tag).toBeNull();
    }
  });

  it("carries no ARR number, no synthetic figure, no result, customer or product claim", () => {
    const t = text();
    const lower = t.toLowerCase();
    // No ARR band or size anywhere. The word ARR appears only in a bottleneck name.
    expect(t).not.toMatch(/\$\d+\s?M|\$20M|\$10M|500\+|ARR band/);
    expect(t).not.toContain("—");
    expect(lower).not.toMatch(
      /proven|\bour customers|testimonial|case stud|synthetic|sample|decision record|what the product does today|deal guidance|salesforce|calculator|coming|cost proxy|win point|system of record|usage or hybrid|usage and hybrid|true margin|trade|evidence_version|cohort/,
    );
    expect(t).not.toMatch(/\$8\.9M|\$67\.1M|2,000/);
    // The only dollar figure is the fee.
    expect(new Set(t.match(/\$[\d,.]+[KMB]?/g) ?? [])).toEqual(new Set(["$7,500"]));
  });

  it("passes the ADR-006 margin guard on every landing string and on the rendered page", () => {
    // Self-check of the shared guard.
    expect(marginViolations("a cost proxy, not margin, until ERP")).toEqual([]);
    expect(marginViolations("thin contribution margin, customer-supplied cost basis.")).toEqual([]);
    expect(marginViolations("thin gross margin")).not.toEqual([]);
    expect(marginViolations("not margin: 40%")).not.toEqual([]);

    const files = [
      "src/app/page.tsx",
      "src/components/HeroHeadline.tsx",
      "src/lib/audit-offer.ts",
      ...readdirSync("src/components/landing").map((f) => "src/components/landing/" + f),
    ];
    for (const f of files) {
      for (const lit of stringLiterals(readFileSync(f, "utf8"))) {
        expect(marginViolations(lit), `${f}: ${lit}`).toEqual([]);
      }
    }
    expect(marginViolations(text())).toEqual([]);
    expect(text()).toContain("contribution margin, customer-supplied cost basis");
  });

  it("left no dead landing components behind", () => {
    expect(readdirSync("src/components/landing")).toEqual(["Bottlenecks.tsx"]);
    const comps = readdirSync("src/components");
    for (const gone of ["DiagnosticPreview.tsx", "WhatYouGet.tsx", "TrustBoundaryStrip.tsx"]) {
      expect(comps).not.toContain(gone);
    }
  });

  it("stays static and exports page metadata through pageMetadata()", () => {
    expect(dynamic).toBe("force-static");
    expect(String(metadata.title)).not.toContain("Pricekeel");
    expect(metadata.alternates?.canonical).toBe("/");
    const d = String(metadata.description);
    expect(d).toContain("We stop AI companies from losing money on heavy users.");
    expect(d.length).toBeGreaterThanOrEqual(70);
    expect(d.length).toBeLessThanOrEqual(160);
    expect(d.toLowerCase()).not.toMatch(/proven|customers/);
    expect(marginViolations(d)).toEqual([]);
    expect(metadata.openGraph?.images).toBeTruthy();
  });
});
