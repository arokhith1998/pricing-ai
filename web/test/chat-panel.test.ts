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
