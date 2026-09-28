// @vitest-environment jsdom
//
// 2026-09-27 external review: the live /pricing hero rendered as an empty
// viewport for some visitors, because Reveal/Stagger bake their hidden state
// (opacity 0) into the server-rendered HTML and only remove it once an
// IntersectionObserver fires (or, for mount-mode, hydration completes). Some
// visitors never get there. These tests pin the fix: the server-rendered
// markup is always visible, and a viewport observer that never fires cannot
// hide content forever.
import { renderToStaticMarkup } from "react-dom/server";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";

// jsdom has no IntersectionObserver. This stub never actually calls back,
// which is exactly the failure mode under test: the fallback timer must
// force the visible state even when the observer never fires.
class NoopIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

beforeEach(() => {
  vi.stubGlobal("IntersectionObserver", NoopIntersectionObserver);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function assertNoHiddenOpacity(html: string) {
  expect(html).not.toMatch(/opacity:\s*0(?!\.)/);
  expect(html).not.toMatch(/opacity="0"/);
}

describe("Reveal server-rendered markup", () => {
  it("never ships opacity 0 for mount-mode content", () => {
    const html = renderToStaticMarkup(
      <Reveal>
        <p>Hero copy</p>
      </Reveal>,
    );
    expect(html).toContain("Hero copy");
    assertNoHiddenOpacity(html);
  });

  it("never ships opacity 0 for inView content, even above the fold", () => {
    const html = renderToStaticMarkup(
      <Reveal inView>
        <p>Above the fold</p>
      </Reveal>,
    );
    expect(html).toContain("Above the fold");
    assertNoHiddenOpacity(html);
  });

  it("never ships opacity 0 for Stagger/StaggerItem grids", () => {
    const html = renderToStaticMarkup(
      <Stagger>
        <StaggerItem>
          <p>Card one</p>
        </StaggerItem>
        <StaggerItem>
          <p>Card two</p>
        </StaggerItem>
      </Stagger>,
    );
    expect(html).toContain("Card one");
    expect(html).toContain("Card two");
    assertNoHiddenOpacity(html);
  });
});

function styleOf(node: HTMLElement | null): string {
  const el = node?.closest<HTMLElement>("div") ?? node;
  return el?.getAttribute("style") ?? "";
}

describe("Reveal client fallback", () => {
  it("stays visible and never hides inView content already on screen at mount", () => {
    Object.defineProperty(HTMLElement.prototype, "getBoundingClientRect", {
      configurable: true,
      value: () => ({ top: 10, bottom: 50, left: 0, right: 0, width: 0, height: 40 }),
    });
    render(
      <Reveal inView>
        <p>On screen</p>
      </Reveal>,
    );
    const node = screen.getByText("On screen");
    expect(node).toBeTruthy();
    expect(styleOf(node)).not.toContain("opacity: 0");
  });

  it("forces the visible state if the viewport observer never fires within the fallback window", () => {
    vi.useFakeTimers();
    Object.defineProperty(HTMLElement.prototype, "getBoundingClientRect", {
      configurable: true,
      value: () => ({ top: 5000, bottom: 5040, left: 0, right: 0, width: 0, height: 40 }),
    });
    render(
      <Reveal inView>
        <p>Below the fold</p>
      </Reveal>,
    );
    // Content is present throughout; the fallback only ever forces it back
    // to fully visible, it never removes it.
    expect(screen.getByText("Below the fold")).toBeTruthy();
    act(() => {
      vi.advanceTimersByTime(900);
    });
    const node = screen.getByText("Below the fold");
    expect(node).toBeTruthy();
    expect(styleOf(node)).not.toContain("opacity: 0");
  });
});
