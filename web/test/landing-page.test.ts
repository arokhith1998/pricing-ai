// @vitest-environment jsdom
//
// The landing-page rewrite (five sections, immersive, honesty-checked) must
// hold three invariants going forward:
//   1. no em dash anywhere in the visible copy (founder calls them an AI-tell)
//   2. two retired marketing claims never come back ("usage or hybrid" and
//      "system of record")
//   3. the hero's one headline number is read from the bundled sample
//      snapshot, not hand-typed, so it moves when the snapshot is
//      regenerated instead of silently going stale.
//
// Written as plain React.createElement calls (no JSX) so this file can stay
// a .ts file and does not need to touch vitest.config.mts's test-file glob,
// matching the pattern in lead-form.test.ts / guidance-client.test.ts.
import { createElement } from "react";
import { cleanup, render } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import sampleFallback from "@/data/sample-fallback.json";
import { moneyShort } from "@/lib/format";
import Landing from "@/app/page";

// jsdom does not implement IntersectionObserver; framer-motion's
// `whileInView` (used by Reveal's inView mode and the diagnostic preview's
// bar chart) constructs one unconditionally. A no-op stub is enough since
// this test only checks rendered text, not scroll-triggered animation.
class StubIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeAll(() => {
  // @ts-expect-error -- test-only global polyfill, jsdom has no real one.
  global.IntersectionObserver = StubIntersectionObserver;
});

afterAll(() => {
  // @ts-expect-error -- undo the polyfill so it never leaks into other files.
  delete global.IntersectionObserver;
});

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
  });

  it("never claims to be a system of record", () => {
    const { container } = render(createElement(Landing));
    expect(container.textContent?.toLowerCase()).not.toContain("system of record");
  });

  it("renders the hero number straight from the bundled sample snapshot", () => {
    const { container } = render(createElement(Landing));
    // moneyShort(8_946_770...) === "$8.9M": whatever the snapshot says today,
    // this recomputes it instead of hard-coding the string, so a future
    // regeneration of sample-fallback.json still passes.
    expect(container.textContent).toContain(moneyShort(HERO_EXCESS));
  });
});
