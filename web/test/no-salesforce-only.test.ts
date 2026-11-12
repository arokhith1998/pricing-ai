import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Founder, 2026-11-11: "we are not sticking to Salesforce alone". The site
// positioning is not Salesforce-only. The /crm product route and the adapter
// code are untouched; this guards the positioning surfaces only.
const FILES = [
  "src/app/layout.tsx",
  "src/lib/site-nav.ts",
  "src/components/Nav.tsx",
  "src/app/page.tsx",
  "src/components/HeroHeadline.tsx",
  "src/components/landing/Bottlenecks.tsx",
  "src/app/contact/page.tsx",
  "src/app/audit/page.tsx",
];

describe("positioning is not Salesforce-only", () => {
  for (const f of FILES) {
    it(`${f} never says "Salesforce deal guidance" or "in Salesforce"`, () => {
      const src = readFileSync(f, "utf8");
      expect(src).not.toMatch(/Salesforce deal guidance/i);
      expect(src).not.toMatch(/\bin Salesforce\b/);
    });
  }

  it("the default title and description follow the hero", () => {
    const src = readFileSync("src/app/layout.tsx", "utf8");
    expect(src).toContain('"Pricekeel · Pricing for AI and B2B software companies"');
    const d = src.match(/DEFAULT_DESCRIPTION =\s*"([^"]+)"/)?.[1] ?? "";
    expect(d).toContain("We stop AI companies from losing money on heavy users.");
    expect(d).toContain("B2B and AI software companies moving from flat or per-seat to usage or outcome pricing");
    expect(d.length).toBeLessThan(160);
    expect(d).not.toMatch(/Salesforce|usage and hybrid/);
  });

  it("no navigation label names Salesforce", () => {
    const nav = readFileSync("src/lib/site-nav.ts", "utf8");
    const labels = [...nav.matchAll(/label:\s*"([^"]+)"/g)].map((m) => m[1]);
    expect(labels.length).toBeGreaterThanOrEqual(5);
    for (const l of labels) expect(l).not.toMatch(/Salesforce/);
  });
});
