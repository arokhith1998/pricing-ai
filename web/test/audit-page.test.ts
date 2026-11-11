// @vitest-environment jsdom
//
// PK-113 invariants for /audit, the one-page offer from
// gtm/ai-margin-audit-offer.md. The wording that protects the trust claim is
// pinned here: the price, the clock, the gate, the cost-basis label (ADR-006,
// ADR-007), and the absence of customers, proof or margin shorthand.
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AuditPage, { dynamic, metadata } from "@/app/audit/page";
import { DECLARED_LABEL, marginViolations, stringLiterals } from "./cost-basis-guard";

afterEach(cleanup);

function renderText() {
  const { container } = render(createElement(AuditPage));
  return { container, text: container.textContent ?? "" };
}

describe("/audit", () => {
  it("states the promise with the contribution-margin label and no recovery guarantee", () => {
    const { text } = renderText();
    expect(text).toContain(
      "In 14 days from validated intake of your billing and cost exports, we show you which customers and plans your inference and storage costs leave with thin or negative contribution margin, customer-supplied cost basis, and we recommend a packaging structure for you to decide on.",
    );
    expect(text).toContain("No guarantee of recovered revenue");
    expect(text).toContain("Every pricing decision stays with you");
  });

  it("pins the price and the clock wording", () => {
    const { text } = renderText();
    expect(text).toContain("$7,500 fixed, paid upfront");
    expect(text).toContain("The 14-day clock starts at validated intake");
    expect(text).toContain("one-business-day readiness check");
    expect(text).toContain("the clock has not started");
    expect(text).toContain("No share of results, no success fee");
    // The only dollar figure on the page is the fee.
    const dollars = text.match(/\$[\d,.]+[KMB]?/g) ?? [];
    expect(new Set(dollars)).toEqual(new Set(["$7,500"]));
  });

  it("states the gate plainly, and the exports, declaration and key map", () => {
    const { container, text } = renderText();
    expect(text).toContain("Before we can accept any file");
    expect(text).toContain("We do not receive any customer cost file until all four of these are in place");
    for (const g of ["data-addendum amendment", "legal entity is formed", "insurance is bound", "engagement letter is signed"]) {
      expect(text).toContain(g);
    }
    expect(text).toContain("Billing exports");
    expect(text).toContain("upload declaration");
    expect(text).toContain("key map");
    expect(text).toContain("No API keys");
    expect(container.querySelector("#gate-h")).not.toBeNull();
  });

  it("covers the six bottlenecks as audit questions, in order", () => {
    const { container } = renderText();
    const qs = [...container.querySelectorAll("[data-question]")];
    expect(qs.map((q) => q.getAttribute("data-question"))).toEqual([
      "cost-floor", "packaging", "value-metric", "variance", "pilots", "bundling",
    ]);
    for (const q of qs) expect(q.querySelectorAll("li").length).toBeGreaterThanOrEqual(2);
  });

  it("states who it is for and not for", () => {
    const { text } = renderText();
    expect(text).toContain("Who it is for, and who it is not for");
    expect(text).toContain("moving from flat-rate or per-seat pricing to usage or outcome pricing");
    expect(text).toContain("not software");
  });

  it("bans gross margin, net margin and any margin outside the cost-basis label or a negation", () => {
    const { text } = renderText();
    expect(text.toLowerCase()).not.toMatch(/gross margin|net margin|true margin/);
    expect(text).toContain(DECLARED_LABEL);
    expect(marginViolations(text)).toEqual([]);
    const src = readFileSync("src/app/audit/page.tsx", "utf8");
    for (const lit of stringLiterals(src)) expect(marginViolations(lit), lit).toEqual([]);
  });

  it("has no em dash, no proof and no customer claims", () => {
    const { text } = renderText();
    expect(text).not.toContain("—");
    expect(text.toLowerCase()).not.toMatch(
      /proven|\b(our|existing|current|past|paying) customers|testimonial|case stud|logos|results from|saved|recovered \$/,
    );
    // No ARR band or result figure on this page.
    expect(text).not.toMatch(/\$(10|20)M|ARR band/);
  });

  it("is one main, one h1, ordered h2s, with a CTA to /contact", () => {
    const { container } = renderText();
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(container.querySelector("main")?.id).toBe("main");
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect([...container.querySelectorAll("h2")].map((h) => h.id)).toEqual([
      "audited-h", "get-h", "need-h", "gate-h", "price-h", "who-h", "cta-h",
    ]);
    const cta = [...container.querySelectorAll('a[href="/contact"]')];
    expect(cta.length).toBeGreaterThanOrEqual(1);
    expect(cta[0].textContent).toContain("Request the audit");
  });

  it("is static, with a bare title and a canonical path", () => {
    expect(dynamic).toBe("force-static");
    expect(metadata.title).toBe("14-day pricing audit");
    expect(metadata.alternates?.canonical).toBe("/audit");
    const d = String(metadata.description);
    expect(d.length).toBeGreaterThanOrEqual(70);
    expect(d.length).toBeLessThanOrEqual(160);
    expect(marginViolations(d)).toEqual([]);
  });
});
