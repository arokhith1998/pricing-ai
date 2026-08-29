import { beforeEach, describe, expect, it, vi } from "vitest";

// Module-boundary mocks, following the pattern in the salesforce-*.test.ts
// suite: mock the DB/cookie/rate-limit boundaries, exercise the real route
// handler logic in between.
const cookieStore = vi.hoisted(() => ({ set: vi.fn() }));
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => cookieStore),
}));

const saveLeadMock = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock("@/lib/store", () => ({ saveLead: saveLeadMock }));

vi.mock("@/lib/ratelimit", () => ({ rateLimit: vi.fn(() => null) }));

import { LEAD_COOKIE } from "@/lib/auth";
import { POST } from "@/app/api/lead/route";

function req(body: Record<string, unknown>) {
  return new Request("https://pricekeel.com/api/lead", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

const validLead = {
  name: "Jane Doe",
  company: "Acme Inc",
  email: "jane@acme.com",
  role_title: "VP Pricing",
  role_function: "Pricing",
  revenue_range: "$10M to $50M",
  pricing_model: "Usage / consumption",
  consent: true,
  utm: {},
};

describe("POST /api/lead honeypot", () => {
  beforeEach(() => {
    cookieStore.set.mockClear();
    saveLeadMock.mockClear();
  });

  it("silently drops a honeypot-tripped submission and never sets the lead cookie", async () => {
    const res = await POST(req({ ...validLead, website: "https://spam.example" }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ ok: true });
    expect(saveLeadMock).not.toHaveBeenCalled();
    expect(cookieStore.set).not.toHaveBeenCalled();
  });

  it("saves the lead and sets the lead cookie on a real submission", async () => {
    const res = await POST(req({ ...validLead, website: "" }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ ok: true });
    expect(saveLeadMock).toHaveBeenCalledTimes(1);
    expect(cookieStore.set).toHaveBeenCalledTimes(1);
    expect(cookieStore.set.mock.calls[0][0]).toBe(LEAD_COOKIE);
  });

  // This is the property the client relies on: a bot cannot distinguish
  // rejection from acceptance by status code or response body, so LeadForm
  // must not either. If this test ever fails because someone "improved" the
  // honeypot response to help the client, that is a regression, not a fix:
  // the fix belongs in LeadForm's own unlock verification.
  it("returns a byte-identical status and body for a honeypot rejection and a real success", async () => {
    const honeypot = await POST(req({ ...validLead, website: "bot-filled-this" }));
    const real = await POST(req({ ...validLead, website: "" }));

    expect(honeypot.status).toBe(real.status);
    expect(await honeypot.json()).toEqual(await real.json());
  });

  it("takes the honeypot branch before field validation, so an incomplete bot submission still gets a plain 200", async () => {
    // The honeypot check runs first in route.ts, on purpose: a bot never
    // sees a 400 or a validation error either, which would otherwise leak
    // which fields it needs to fill in to pass.
    const res = await POST(
      req({ email: "", company: "", consent: true, website: "bot-filled-this" }),
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
  });
});
