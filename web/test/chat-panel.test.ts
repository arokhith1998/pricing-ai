// @vitest-environment jsdom
//
// Silent-failure-hunter finding 4: /api/copilot/route.ts used to forward the
// raw upstream body as `error` and collapse every non-2xx status to 502, so
// ChatPanel showed the same generic message for a validation error (4xx,
// fixable by the user) as for the LLM actually being down (5xx). This
// exercises the real component (not the route, covered in
// copilot-route.test.ts) against a stubbed /api/copilot fetch, mirroring
// guidance-client.test.ts's "shows the backend's own message on a 4xx
// instead of a generic one" pattern.
import { createElement } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ChatPanel from "@/components/ChatPanel";
import type { Diagnostic } from "@/lib/api";

const analysis = {} as unknown as Diagnostic;

const CANONICAL = { questions: [{ id: "q1", label: "Where is discount leaking?", hint: "hint" }] };

function stubFetch(postResponse: Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/api/copilot") && (!init || init.method === undefined)) {
        return new Response(JSON.stringify(CANONICAL), { status: 200 });
      }
      if (String(url).includes("/api/copilot") && init?.method === "POST") {
        return postResponse;
      }
      return new Response(JSON.stringify(CANONICAL), { status: 200 });
    }),
  );
}

async function openAndAsk() {
  render(createElement(ChatPanel, { analysis }));
  screen.getByRole("button", { name: /ask your pricekeel/i }).click();
  const question = await screen.findByText(/where is discount leaking/i);
  question.click();
}

describe("ChatPanel copilot error handling distinguishes 4xx from 5xx", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the backend's own detail on a 4xx", async () => {
    stubFetch(
      new Response(JSON.stringify({ error: "qid must be one of the six canonical questions" }), {
        status: 422,
      }),
    );
    await openAndAsk();
    await waitFor(() =>
      screen.getByText(/qid must be one of the six canonical questions/i),
    );
    expect(screen.queryByText(/copilot is unavailable/i)).toBeNull();
  });

  it("shows a generic unavailable message on a 5xx instead of the raw upstream body", async () => {
    stubFetch(new Response(JSON.stringify({ error: "<html>upstream 503 noise</html>" }), { status: 502 }));
    await openAndAsk();
    await waitFor(() => screen.getByText(/copilot is unavailable/i));
    expect(screen.queryByText(/upstream 503 noise/i)).toBeNull();
  });
});

// pricing/copilot.py's Answer.narrated is false when no LLM provider is
// configured server-side: `text` is then the engine's own fallback line
// ("Pricekeel: I would normally narrate..."), not model-generated prose.
// Presenting that as a normal chat bubble reads as an apologetic reply from
// a model, so ChatPanel must label it plainly instead (2026-09-27 review).
describe("ChatPanel narration-off banner (narrated: false)", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  const OPPORTUNITY = {
    id: "opp-1",
    kind: "investigate",
    scope: "Enterprise segment",
    current: "18% average discount",
    recommended: "Review against the win point",
    revenue_impact_usd: 42_000,
    confidence: 0.7,
    evidence: [],
    methodology: "reference-discount",
  };

  it("shows the narration-off banner instead of the apology text, and keeps the opportunities", async () => {
    stubFetch(
      new Response(
        JSON.stringify({
          text: "Pricekeel: I would normally narrate the 1 opportunity...",
          opportunities: [OPPORTUNITY],
          narrated: false,
        }),
        { status: 200 },
      ),
    );
    await openAndAsk();
    await waitFor(() => screen.getByText(/ai narration is off on this server/i));
    expect(screen.queryByText(/i would normally narrate/i)).toBeNull();
    screen.getByText(/enterprise segment/i);
  });

  it("shows the narrated text normally when narrated is true", async () => {
    stubFetch(
      new Response(
        JSON.stringify({
          text: "Discount is concentrated in the enterprise segment.",
          opportunities: [OPPORTUNITY],
          narrated: true,
        }),
        { status: 200 },
      ),
    );
    await openAndAsk();
    await waitFor(() => screen.getByText(/discount is concentrated/i));
    expect(screen.queryByText(/ai narration is off on this server/i)).toBeNull();
  });

  it("treats a missing narrated field (an older cached response) as narrated", async () => {
    stubFetch(
      new Response(
        JSON.stringify({
          text: "Discount is concentrated in the enterprise segment.",
          opportunities: [OPPORTUNITY],
        }),
        { status: 200 },
      ),
    );
    await openAndAsk();
    await waitFor(() => screen.getByText(/discount is concentrated/i));
    expect(screen.queryByText(/ai narration is off on this server/i)).toBeNull();
  });
});
