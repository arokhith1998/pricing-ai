// @vitest-environment jsdom
//
// PK-116 (F17) invariants for /audit: the offer on one short page. Under 350
// words, in a fixed order, one booking button, and the wording that protects
// the trust claim (price, delivery guarantee, ADR-006 label, no proof, no
// customers, no outcome promise).
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AuditPage, { dynamic, metadata } from "@/app/audit/page";
import { BOOKING_LABEL, BOOKING_URL } from "@/lib/site-nav";
import { DECLARED_LABEL, marginViolations, stringLiterals } from "./cost-basis-guard";

afterEach(cleanup);

function renderText() {
  const { container } = render(createElement(AuditPage));
  return { container, text: container.textContent ?? "" };
}

// Visible words: text nodes joined with spaces so element boundaries do not fuse words.
export function wordCount(container: HTMLElement): number {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const parts: string[] = [];
  while (walker.nextNode()) parts.push(walker.currentNode.textContent ?? "");
  return parts.join(" ").split(/\s+/).filter(Boolean).length;
}

describe("/audit", () => {
  it("is under 350 words", () => {
    const { container } = renderText();
    expect(wordCount(container)).toBeLessThan(350);
    expect(wordCount(container)).toBeGreaterThan(150);
  });

  it("has one h1 with the promise, then the sections in the decided order", () => {
    const { container } = renderText();
    const h1 = container.querySelectorAll("h1");
    expect(h1).toHaveLength(1);
    expect(h1[0].textContent).toBe("Find which customers cost you more than they pay.");
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(container.querySelector("main")?.id).toBe("main");
    expect([...container.querySelectorAll("h2")].map((h) => h.id)).toEqual([
      "get-h", "how-h", "need-h", "price-h", "who-h",
    ]);
    const eyebrows = [...container.querySelectorAll("h2")].map(
      (h) => h.previousElementSibling?.textContent,
    );
    expect(eyebrows).toEqual(["What you get", "How it works", "What we need", "Price", "Who it is for"]);
    const bands = [...container.querySelectorAll("main > section")].map((s) => s.getAttribute("data-band"));
    for (let i = 1; i < bands.length; i++) expect(bands[i]).not.toBe(bands[i - 1]);
  });

  it("says what you get, with the cost-basis label", () => {
    const { text } = renderText();
    expect(text).toContain("14-day, done-for-you audit of your billing and cost exports");
    expect(text).toContain(`Each customer and plan with its ${DECLARED_LABEL}.`);
    expect(text).toContain("The usage level where each plan stops covering its cost.");
    expect(text).toContain("One recommended packaging structure and two alternatives, for you to decide.");
    expect(text).toContain("A 60-minute readout and a PDF your finance lead can forward.");
  });

  it("lists the three steps, with the clock starting when files check out", () => {
    const { container, text } = renderText();
    const steps = [...container.querySelectorAll("#how-h ~ ol > li")].map((l) => l.textContent);
    expect(steps).toHaveLength(3);
    expect(steps[0]).toContain("Talk to us.");
    expect(steps[0]).toContain("No data, no access.");
    expect(steps[1]).toContain("mutual NDA and data addendum");
    expect(steps[1]).toContain("customers replaced by codes");
    expect(steps[2]).toContain("Get the readout in 14 days.");
    expect(text).toContain("from the day your files arrive and check out");
    expect(text.toLowerCase()).not.toContain("validated intake");
  });

  it("lists what we need and what we do not take", () => {
    const { container, text } = renderText();
    const need = [...container.querySelectorAll("#need-h ~ ul > li")].map((l) => l.textContent);
    expect(need).toEqual([
      "Billing exports",
      "Model-provider and cloud cost exports",
      "A customer list with plan and start date",
      "One person who owns pricing",
    ]);
    expect(text).toContain("No API keys, no prompts, no end-user data.");
  });

  it("pins the price, the delivery guarantee, the subscription line and the decision line", () => {
    const { container, text } = renderText();
    expect(text).toContain("$7,500 fixed, paid upfront.");
    expect(container.querySelector('[data-testid="delivery-guarantee"]')?.textContent).toBe(
      "If we do not deliver the 14-day readout, you pay nothing.",
    );
    expect(container.querySelector('[data-testid="follow-on"]')?.textContent).toBe(
      "An ongoing subscription is available after the audit, priced with you.",
    );
    expect(text).toContain("We recommend, you decide; we do not promise recovered revenue.");
    expect(
      container
        .querySelector("#price-h")
        ?.closest("section")
        ?.contains(container.querySelector('[data-testid="delivery-guarantee"]')),
    ).toBe(true);
    // The only dollar figure is the fee; the subscription has none.
    expect(new Set(text.match(/\$[\d,.]+[KMB]?/g) ?? [])).toEqual(new Set(["$7,500"]));
  });

  it("states who it is for and the readiness line", () => {
    const { container, text } = renderText();
    expect(text).toContain(
      "Companies moving from flat or per-seat pricing to usage or outcome pricing, with at least 10 billed customers and 3 months of billing history.",
    );
    expect(container.querySelector('[data-testid="readiness"]')?.textContent).toBe(
      "We take no files until the paperwork is signed; a conversation needs none.",
    );
  });

  it("has one button, the booking label and constant", () => {
    const { container } = renderText();
    const links = [...container.querySelectorAll("main a")];
    expect(links).toHaveLength(1);
    expect(links[0].textContent).toBe(BOOKING_LABEL);
    expect(links[0].getAttribute("href")).toBe(BOOKING_URL);
  });

  it("dropped the six questions, twelve deliverables, gate, credit terms and Request the audit", () => {
    const { text } = renderText();
    const lower = text.toLowerCase();
    for (const gone of [
      "six questions", "deliverables", "the gate", "insurance", "engagement letter is signed",
      "credit toward", "readiness check", "request the audit", "benchmarking", "key map", "declaration",
      "not for", "software.",
    ]) {
      expect(lower, gone).not.toContain(gone);
    }
  });

  it("bans gross margin, net margin and any margin outside the cost-basis label or a negation", () => {
    const { text } = renderText();
    expect(text.toLowerCase()).not.toMatch(/gross margin|net margin|true margin/);
    expect(text).toContain(DECLARED_LABEL);
    expect(marginViolations(text)).toEqual([]);
    const src = readFileSync("src/app/audit/page.tsx", "utf8");
    for (const lit of stringLiterals(src)) expect(marginViolations(lit), lit).toEqual([]);
  });

  it("has no em dash, no proof, no customer claims and no outcome promise", () => {
    const { text } = renderText();
    const src = readFileSync("src/app/audit/page.tsx", "utf8");
    for (const t of [text, src]) expect(t).not.toContain("—");
    const lower = text.toLowerCase();
    expect(lower).not.toMatch(
      /proven|\b(our|existing|current|past|paying) customers|testimonial|case stud|logos|results from|saved|recovered \$|money.back|boost|autonomous/,
    );
    expect(lower).not.toMatch(/increas\w*[^.]{0,60}margin|margin[^.]{0,60}increas|improv\w*[^.]{0,40}margin/);
    expect(text).not.toMatch(/\$(10|20)M|ARR band|salesforce/i);
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
