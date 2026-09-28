import { afterEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 4: /api/copilot/route.ts's forwardJson used
// to dump the raw upstream body into `error` and flatten every non-2xx
// status to 502. This exercises the route handler directly against a
// stubbed FastAPI response.

vi.mock("@/lib/gate", () => ({
  requireLead: vi.fn(async () => null),
  customerRef: vi.fn(async () => "demo:tenant"),
}));

import { POST } from "@/app/api/copilot/route";

function req(body: Record<string, unknown>) {
  return new Request("https://pricekeel.com/api/copilot", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/copilot forwards upstream status and detail", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards a 422 and its detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ detail: "qid is required" }, { status: 422 })),
    );
    const res = await POST(req({ action: "canonical" }));
    expect(res.status).toBe(422);
    expect(await res.json()).toEqual({ error: "qid is required" });
  });

  it("collapses a 5xx to a generic 502, not the raw body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>internal server error</html>", { status: 503 })),
    );
    const res = await POST(req({ action: "canonical" }));
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.error).not.toMatch(/internal server error/i);
  });

  it("keeps 401/403 as a 502 (a shared-secret problem, not a fixable input)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ detail: "invalid API key" }, { status: 401 })),
    );
    const res = await POST(req({ action: "canonical" }));
    expect(res.status).toBe(502);
  });
});
