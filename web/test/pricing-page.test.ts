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
      "$20 to 100M",
    ]) {
      expect(text).not.toContain(phrase);
    }
    expect(text).not.toMatch(/\$20(?!K)/);
  });

  it("keeps the D-R6 wording and the corrected ARR band", () => {
    const { text } = renderText();
    expect(text).toContain("We expect");
    expect(text).toContain("we will reply within one business day");
    expect(text).toContain("$10M");
  });

  it("renders exactly two tier cards and a roadmap line with no button or link", () => {
    const { container } = renderText();
    const tiers = container.querySelectorAll("[data-tier]");
    expect(tiers).toHaveLength(2);
    expect(Array.from(tiers).map((t) => t.getAttribute("data-tier"))).toEqual([
      "diagnostic",
      "operate",
    ]);
    for (const t of tiers) expect(t.querySelector("a[href='/contact']")).not.toBeNull();
    const roadmap = container.querySelector("[data-roadmap]");
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
      const stripped = own.replace(/\$10M to \$100M ARR/g, "");
      if (el.querySelector("p, li")) continue; // container, children are checked
      expect(stripped, own).not.toMatch(/\$\d|\d%/);
    }
  });

  it("is on main#main, uses Link for /contact, and has one h1", () => {
    const { container } = renderText();
    const main = container.querySelector("main");
    expect(main?.id).toBe("main");
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(container.querySelector(".pk-upside-glow")).toBeNull();
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
