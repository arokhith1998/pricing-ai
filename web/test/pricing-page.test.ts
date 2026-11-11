// @vitest-environment jsdom
//
// PK-77 invariants for /pricing: the claims that exceeded the evidence stay
// gone, the D-R6 wording stays in, two tiers (no third tier card), the roadmap
// line has no button, and every hand-built figure carries a provenance label.
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import PricingPage, { metadata } from "@/app/pricing/page";

afterEach(cleanup);

function renderText() {
  const { container } = render(createElement(PricingPage));
  return { container, text: container.textContent ?? "" };
}

describe("/pricing", () => {
  it("drops the claims that exceed the evidence", () => {
    const { text } = renderText();
    for (const phrase of [
      "typically start",
      "open code",
      "Most subscribers",
      "Worth the subscription",
      "$20M",
    ]) {
      expect(text).not.toContain(phrase);
    }
    expect(text).not.toMatch(/\$20(?!K)/);
  });

  it("keeps the D-R6 wording and the corrected ARR band", () => {
    const { text } = renderText();
    expect(text).toContain("We expect");
    expect(text).toContain("we will reply within one business day");
    expect(text).toContain("$10M to $100M ARR");
  });

  it("renders exactly three tier cards, the audit first, and a roadmap line with no button or link", () => {
    const { container } = renderText();
    const tiers = container.querySelectorAll("[data-tier]");
    expect(tiers).toHaveLength(3);
    expect(Array.from(tiers).map((t) => t.getAttribute("data-tier"))).toEqual([
      "audit",
      "diagnostic",
      "operate",
    ]);
    for (const t of tiers) expect(t.querySelector("a[href='/contact']")).not.toBeNull();
    const audit = container.querySelector("[data-tier='audit']")!;
    expect(audit.querySelector("[data-price]")?.textContent).toBe("$7,500 fixed, 14 days");
    expect(audit.textContent).toContain("Paid upfront. The clock starts at validated intake.");
    expect(audit.textContent).toContain("No guarantee of recovered revenue");
    expect(audit.querySelector("a[href='/audit']")).not.toBeNull();
    expect(audit.textContent?.toLowerCase()).not.toMatch(/gross margin|net margin|proven/);
    const roadmap = container.querySelector("[data-roadmap='data-expansion']");
    expect(roadmap).not.toBeNull();
    expect(roadmap?.querySelector("a, button")).toBeNull();
    expect(roadmap?.closest("[data-tier]")).toBeNull();
  });

  it("labels every hand-built figure as illustrative", () => {
    const { container } = renderText();
    const blocks = container.querySelectorAll("[data-scenario], [data-threshold]");
    expect(blocks.length).toBe(7);
    for (const b of blocks) {
      expect(b.querySelector("[data-synthetic-tag='illustrative']")).not.toBeNull();
    }
    // No dollar figure or percentage sits outside a labelled block, a tier,
    // or the one hero sentence about the ARR band.
    const labelled = Array.from(blocks);
    const walker = container.querySelectorAll("p, li, h2, h3");
    for (const el of walker) {
      if (labelled.some((b) => b.contains(el))) continue;
      const own = el.textContent ?? "";
      let stripped = own.replace(/\$10M to \$100M ARR/g, "");
      // The audit tier may state only its fixed fee and the 14-day clock (F4).
      if (container.querySelector("[data-tier='audit']")?.contains(el)) {
        stripped = stripped.replace(/\$7,500/g, "").replace(/\b14\b/g, "");
      }
      if (el.querySelector("p, li")) continue; // container, children are checked
      expect(stripped, own).not.toMatch(/\$\d|\d%/);
    }
  });

  it("labels unbuilt Operate features as roadmap", () => {
    const { container } = renderText();
    const badges = Array.from(container.querySelectorAll("[data-roadmap='feature']"));
    expect(badges).toHaveLength(3);
    for (const b of badges) expect(b.textContent).toMatch(/roadmap/i);
    const host = (needle: string) =>
      Array.from(container.querySelectorAll("li")).find(
        (li) => li.textContent?.includes(needle) && li.querySelector("[data-roadmap='feature']"),
      );
    expect(host("Monthly drift readout")).toBeTruthy();
    expect(host("Quarterly policy re-simulation")).toBeTruthy();
    expect(host("Defended-vs-investigate dashboard")).toBeTruthy();
    expect(container.textContent).not.toContain("updated weekly");
  });

  it("states the over-discounting arithmetic correctly", () => {
    const { text } = renderText();
    expect(text).toContain("Over-discounting caught");
    expect(text).not.toContain("Caught underdiscounting");
    expect(text).toContain("$30K to $100K per year");
    expect(4 * 250_000 * 0.03).toBe(30_000);
    expect(8 * 250_000 * 0.05).toBe(100_000);
  });

  it("is on main#main, links every tier to /contact through Link, and has one h1", () => {
    const { container } = renderText();
    const main = container.querySelector("main");
    expect(main?.id).toBe("main");
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(container.querySelector(".pk-upside-glow")).toBeNull();
    const links = [...container.querySelectorAll("[data-tier] a")];
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["/contact", "/audit", "/contact", "/contact"]);
    expect(links[0].textContent).toContain("Request the audit");
    for (const a of [links[2], links[3]]) expect(a.textContent).toContain("Talk to us");
  });

  it("has no em dash", () => {
    const { text } = renderText();
    expect(text).not.toContain("—");
  });

  it("sets the bare title so the template renders Pricing · Pricekeel once", () => {
    expect(metadata.title).toBe("Pricing");
    expect(metadata.alternates?.canonical).toBe("/pricing");
    const desc = String(metadata.description);
    expect(desc.length).toBeGreaterThanOrEqual(70);
    expect(desc.length).toBeLessThanOrEqual(160);
  });
});
