import { beforeEach, describe, expect, it, vi } from "vitest";

// Silent-failure-hunter finding 6: two parallel first requests from the same
// page load (e.g. a guidance recommendation fetch and a decision-log read,
// both firing on mount) used to each mint their own demo tenant id when
// neither had a pk_demo_tenant cookie yet, so the browser kept only the last
// Set-Cookie and decisions logged under the other tenant became unreadable.
//
// The fix moves minting to src/proxy.ts, which runs on the page navigation
// itself (before any client-side fetch can fire) and forwards the id it
// established via the X-Pk-Demo-Tenant request header. This test proves the
// consuming half of that fix: customerRef() trusts the forwarded header
// instead of re-deriving (or re-minting) the tenant from cookies, so two
// separate calls that each carry the SAME forwarded header, exactly what
// proxy would produce for two requests it has already stamped, resolve to
// the identical tenant even though neither request's own cookie jar has the
// cookie yet (it has not round-tripped back from the browser in this
// simulation, matching the real race window).
type FakeJar = {
  get: (name: string) => { name: string; value: string } | undefined;
  set: (name: string, value: string) => void;
};

function emptyJar(): FakeJar {
  return { get: () => undefined, set: vi.fn() };
}

const state = vi.hoisted(() => ({
  jar: null as FakeJar | null,
  forwardedTenant: null as string | null,
}));

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => state.jar),
  headers: vi.fn(async () => {
    const h = new Headers();
    if (state.forwardedTenant) h.set("x-pk-demo-tenant", state.forwardedTenant);
    return h;
  }),
}));

vi.mock("@/lib/store", () => ({ isValidAccessCode: vi.fn(async () => false) }));

import { customerRef } from "@/lib/gate";

describe("customerRef trusts proxy's X-Pk-Demo-Tenant header", () => {
  beforeEach(() => {
    state.jar = emptyJar();
    state.forwardedTenant = null;
  });

  it("shares one tenant across two 'parallel' requests proxy already stamped, even with no cookie yet", async () => {
    state.forwardedTenant = "shared-tenant-uuid";

    // Two separate requests (their own fresh cookie jars, as two concurrent
    // HTTP requests would have), both carrying the header proxy set after
    // establishing the tenant on the preceding page navigation.
    state.jar = emptyJar();
    const first = await customerRef();
    state.jar = emptyJar();
    const second = await customerRef();

    expect(first).toBe("demo:shared-tenant-uuid");
    expect(second).toBe("demo:shared-tenant-uuid");
  });

  it("never mints (never sets a cookie) when the header is present", async () => {
    state.forwardedTenant = "shared-tenant-uuid";
    const jar = emptyJar();
    state.jar = jar;
    await customerRef();
    expect(jar.set).not.toHaveBeenCalled();
  });

  it("falls back to minting its own tenant, and logs, when proxy did not forward a header", async () => {
    state.forwardedTenant = null;
    const jar = emptyJar();
    state.jar = jar;
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const ref = await customerRef();
    expect(ref).toMatch(/^demo:[0-9a-f-]{36}$/i);
    expect(jar.set).toHaveBeenCalledTimes(1);
    expect(warn).toHaveBeenCalledWith(expect.stringMatching(/proxy/i));
    warn.mockRestore();
  });
});
