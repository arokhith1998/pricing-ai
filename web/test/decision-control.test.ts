// @vitest-environment jsdom
//
// Silent-failure-hunter finding 7 (NIT): POST /exceptions returns `persisted`
// (governance.py) but DecisionControl.tsx never rendered it, so a decision
// that only landed in the in-memory fallback (DATABASE_URL unavailable) read
// exactly like a durably logged one.
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import DecisionControl from "@/components/DecisionControl";

function verdictResponse(persisted: boolean | undefined) {
  return {
    id: "exc-1",
    created_at: "2026-09-27T00:00:00Z",
    ...(persisted === undefined ? {} : { persisted }),
    verdict: {
      requested_pct: 10,
      recommended_pct: 8,
      floor_pct: 15,
      below_floor: false,
      ev_delta_vs_recommended: 0,
      win_prob_at_requested: 0.5,
      win_prob_at_recommended: 0.5,
      rationale: "Within policy.",
    },
  };
}

async function approve() {
  render(
    createElement(DecisionControl, {
      dealId: "opp-1",
      account: "Acme Inc",
      recommendedDiscount: 0.08,
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: /approve at recommended/i }));
  fireEvent.change(screen.getByLabelText(/approved by/i), { target: { value: "Jane" } });
  fireEvent.click(screen.getByRole("button", { name: /log approval at/i }));
  await waitFor(() => screen.getByText(/logged\./i));
}

describe("DecisionControl renders the persisted flag from /exceptions", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows a durability warning when persisted is false", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(verdictResponse(false)), { status: 200 })),
    );
    await approve();
    screen.getByText(/not durably recorded/i);
  });

  it("shows no durability warning when persisted is true", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(verdictResponse(true)), { status: 200 })),
    );
    await approve();
    expect(screen.queryByText(/not durably recorded/i)).toBeNull();
  });

  it("shows no durability warning when persisted is omitted (older cached response)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(verdictResponse(undefined)), { status: 200 })),
    );
    await approve();
    expect(screen.queryByText(/not durably recorded/i)).toBeNull();
  });
});
