// @vitest-environment jsdom
//
// 2026-09-27 external review: the unlocked /diagnostic page (past the lead
// gate) overflowed at a 390px viewport (~685px scrollWidth, horizontal
// scrollbar, spilled tables, the copilot launcher obstructing content). The
// gated /sample teaser was fine at 390px; the bug lived specifically in the
// full report sections that only render once a lead is captured. This test
// renders that same tree (via the PRICEKEEL_DEV_UNLOCK bypass documented in
// web/.env.example, exercised structurally here rather than over HTTP) using
// the bundled sample data, and pins the two structural invariants the
// mobile-overflow review called for: every table stays inside a horizontally
// scrollable wrapper (so it can never widen the page itself), and nothing in
// the tree ships an inline pixel width wider than the narrowest viewport
// this must support.
import { describe, expect, it, vi } from "vitest";

import type { Diagnostic } from "@/lib/api";
import sampleFallback from "@/data/sample-fallback.json";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getDemo: vi.fn(async () => sampleFallback as unknown as Diagnostic),
  };
});

const MAX_INLINE_PX = 360;

describe("unlocked /diagnostic at a 390px viewport", () => {
  it("keeps every <table> inside an overflow-x-auto ancestor, and ships no inline width above 360px", async () => {
    const { renderToStaticMarkup } = await import("react-dom/server");
    const { default: DiagnosticPage } = await import("@/app/diagnostic/page");

    // DiagnosticPage is an async server component; calling it directly (the
    // same way Next's RSC runtime would) yields the element tree without
    // needing a running server.
    const element = await DiagnosticPage();
    const html = renderToStaticMarkup(element);
    document.body.innerHTML = html;

    const tables = document.body.querySelectorAll("table");
    // Sanity: the fixture actually exercises tables (receipts, top-leak
    // deals, value-metric reference), or this test would pass vacuously.
    expect(tables.length).toBeGreaterThan(0);
    tables.forEach((table) => {
      expect(table.closest(".overflow-x-auto")).not.toBeNull();
    });

    const widthPx = /^(\d+(?:\.\d+)?)px$/;
    document.body.querySelectorAll<HTMLElement>("[style]").forEach((el) => {
      const match = widthPx.exec(el.style.width);
      if (!match) return;
      expect(Number(match[1])).toBeLessThanOrEqual(MAX_INLINE_PX);
    });
  });
});
