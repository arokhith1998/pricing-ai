import { beforeEach, describe, expect, it, vi } from "vitest";

// Module-boundary mocks, following the pattern in lead-route.test.ts: a fake
// cookie jar standing in for next/headers' cookies(), swapped between two
// "visitors" (jarA / jarB) to prove the demo tenant is per-browser, not
// process-wide.
type FakeJar = {
  get: (name: string) => { name: string; value: string } | undefined;
  set: (name: string, value: string) => void;
};

function makeJar(): FakeJar {
  const store = new Map<string, string>();
  return {
    get: (name) => (store.has(name) ? { name, value: store.get(name)! } : undefined),
    set: (name, value) => {
      store.set(name, value);
    },
  };
}

const state = vi.hoisted(() => ({ jar: null as FakeJar | null }));
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => state.jar),
}));

// No access code cookie is ever set in these tests, so verifyAccessCookieValue
// short-circuits on the missing cookie before this is called — mocked anyway
// so the test never touches the Neon/store module boundary.
vi.mock("@/lib/store", () => ({ isValidAccessCode: vi.fn(async () => false) }));

import { customerRef } from "@/lib/gate";

describe("customerRef (per-visitor demo tenant)", () => {
  let jarA: FakeJar;
  let jarB: FakeJar;

  beforeEach(() => {
    jarA = makeJar();
    jarB = makeJar();
  });

  it("mints a demo:<uuid> tenant for a lead-gated visitor with no access code", async () => {
    state.jar = jarA;
    const ref = await customerRef();
    expect(ref).toMatch(/^demo:[0-9a-f-]{36}$/i);
  });

  it("is stable across repeated calls for the same cookie jar", async () => {
    state.jar = jarA;
    const first = await customerRef();
    const second = await customerRef();
    expect(second).toBe(first);
  });

  it("gives two different lead cookies different customerRefs", async () => {
    state.jar = jarA;
    const a = await customerRef();
    state.jar = jarB;
    const b = await customerRef();
    expect(a).not.toBe(b);
  });
});
