import { beforeEach, describe, expect, it, vi } from "vitest";

// Module-boundary mocks, following the pattern in lead-route.test.ts: mock
// the FastAPI client and the email sender, exercise the real route handler
// logic in between.
const getDigestAllMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ getDigestAll: getDigestAllMock }));

const sendDigestMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/notify", () => ({ sendDigest: sendDigestMock }));

import { POST } from "@/app/api/digest/send/route";

function req(headers: Record<string, string> = {}) {
  return new Request("https://pricekeel.com/api/digest/send", {
    method: "POST",
    headers,
  });
}

function digestFor(customer: string) {
  return {
    customer,
    generated_at: "2026-09-27T00:00:00Z",
    window_days: 7,
    headline: `headline for ${customer}`,
    lines: [],
    stats: {
      exceptions_total: 1,
      exceptions_below_floor: 0,
      copilot_decisions: 0,
      realization_pct: 80.0,
      excess_vs_segment_reference: 1000.0,
    },
    book_source: "demo" as const,
  };
}

describe("POST /api/digest/send", () => {
  beforeEach(() => {
    getDigestAllMock.mockReset();
    sendDigestMock.mockReset();
    delete process.env.CRON_SECRET;
    // NODE_ENV is "test" under vitest by default, so the CRON_SECRET-unset
    // path below takes the dev "allow" branch, not the production 503.
  });

  it("sends one email per active tenant, never the unused default bucket", async () => {
    const acme = digestFor("ACME-CODE");
    const bravo = digestFor("BRAVO-CODE");
    getDigestAllMock.mockResolvedValue({
      digests: [acme, bravo],
      customers: ["ACME-CODE", "BRAVO-CODE"],
    });
    sendDigestMock.mockImplementation(async () => ({
      sent_to: "founder@pricekeel.com",
      dry_run: false,
    }));

    const res = await POST(req());
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(sendDigestMock).toHaveBeenCalledTimes(2);
    expect(sendDigestMock).toHaveBeenCalledWith(acme);
    expect(sendDigestMock).toHaveBeenCalledWith(bravo);
    expect(body.ok).toBe(true);
    expect(body.sent_count).toBe(2);
    expect(body.sent.map((s: { customer: string }) => s.customer).sort()).toEqual([
      "ACME-CODE",
      "BRAVO-CODE",
    ]);
    expect(body.failed).toEqual([]);
  });

  it("reports a dry run with no tenants when nobody has activity", async () => {
    getDigestAllMock.mockResolvedValue({ digests: [], customers: [] });

    const res = await POST(req());
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ ok: true, dry_run: true, customers: [] });
    expect(sendDigestMock).not.toHaveBeenCalled();
  });

  it("does not let one tenant's send failure block the others", async () => {
    const acme = digestFor("ACME-CODE");
    const bravo = digestFor("BRAVO-CODE");
    getDigestAllMock.mockResolvedValue({
      digests: [acme, bravo],
      customers: ["ACME-CODE", "BRAVO-CODE"],
    });
    sendDigestMock.mockImplementation(async (d: { customer: string }) => {
      if (d.customer === "ACME-CODE") throw new Error("resend down");
      return { sent_to: "founder@pricekeel.com", dry_run: false };
    });

    const res = await POST(req());
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.ok).toBe(false);
    expect(body.failed).toEqual(["ACME-CODE"]);
    expect(body.sent_count).toBe(1);
  });

  it("returns 502 when the digest fetch itself fails", async () => {
    getDigestAllMock.mockRejectedValue(new Error("API down"));

    const res = await POST(req());
    expect(res.status).toBe(502);
    expect(sendDigestMock).not.toHaveBeenCalled();
  });
});
