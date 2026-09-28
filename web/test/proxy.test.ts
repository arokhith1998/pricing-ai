import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { ACCESS_COOKIE, DEMO_TENANT_COOKIE, DEMO_TENANT_HEADER } from "@/lib/auth";
import { proxy } from "@/proxy";

function diagnosticReq() {
  return new NextRequest("https://pricekeel.com/diagnostic");
}

// A path outside both pre-existing page-gating branches (/upload,/crm,
// /competitor-watch need an access code; /diagnostic,/guidance need a lead)
// so these tests exercise only the demo-tenant minting this file adds,
// without exercising (or depending on) that unrelated redirect logic.
function req(cookieHeader = "") {
  return new NextRequest("https://pricekeel.com/api/exceptions", {
    headers: cookieHeader ? { cookie: cookieHeader } : undefined,
  });
}

function setCookieValue(response: Response, name: string): string | null {
  // Response.headers.getSetCookie is the standard way to read multiple
  // Set-Cookie headers; NextResponse extends Response.
  const all =
    typeof response.headers.getSetCookie === "function"
      ? response.headers.getSetCookie()
      : [response.headers.get("set-cookie") ?? ""].filter(Boolean);
  const match = all.find((line) => line.startsWith(`${name}=`));
  if (!match) return null;
  return match.slice(name.length + 1).split(";")[0];
}

// NextResponse.next({ request: { headers } }) does not surface the rewritten
// *request* headers on response.headers.get(name) directly (that would be
// the response sent to the browser); Next encodes the downstream-only
// request-header rewrite internally as x-middleware-request-<name>, which
// its runtime decodes back into the destination's request.headers before a
// route handler or page ever sees it. Reading that internal encoding is how
// this test verifies proxy forwarded the header without a full request/
// response harness.
function forwardedRequestHeader(response: Response, name: string): string | null {
  return response.headers.get(`x-middleware-request-${name}`);
}

describe("proxy (Next.js 16's middleware, src/proxy.ts)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("without a lead cookie, /diagnostic redirects to /sample (the gate is on by default)", async () => {
    const response = await proxy(diagnosticReq());
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/sample");
  });

  it("PRICEKEEL_DEV_UNLOCK=1 bypasses the lead gate on /diagnostic outside production", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("PRICEKEEL_DEV_UNLOCK", "1");
    const response = await proxy(diagnosticReq());
    expect(response.status).not.toBe(307);
    expect(response.headers.get("location")).toBeFalsy();
  });

  it("PRICEKEEL_DEV_UNLOCK=1 is ignored when NODE_ENV is production", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("PRICEKEEL_DEV_UNLOCK", "1");
    const response = await proxy(diagnosticReq());
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/sample");
  });

  it("mints a demo tenant and forwards it via both Set-Cookie and the request header when neither cookie is present", async () => {
    const response = await proxy(req());
    const cookieValue = setCookieValue(response, DEMO_TENANT_COOKIE);
    expect(cookieValue).toBeTruthy();
    const forwardedId = forwardedRequestHeader(response, DEMO_TENANT_HEADER);
    expect(forwardedId).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("does not mint a second tenant once a valid cookie already exists (the second of two 'parallel' requests)", async () => {
    const first = await proxy(req());
    const cookieValue = setCookieValue(first, DEMO_TENANT_COOKIE);
    const firstId = forwardedRequestHeader(first, DEMO_TENANT_HEADER);
    expect(cookieValue).toBeTruthy();

    // Simulate the second request, arriving after the browser applied the
    // first response's Set-Cookie (the realistic ordering: the page
    // navigation's proxy invocation runs, and completes, before any
    // client-side fetch the page fires can reach the server).
    const second = await proxy(req(`${DEMO_TENANT_COOKIE}=${cookieValue}`));
    expect(setCookieValue(second, DEMO_TENANT_COOKIE)).toBeNull();
    expect(forwardedRequestHeader(second, DEMO_TENANT_HEADER)).toBe(firstId);
  });

  it("skips minting entirely for an access-code visitor", async () => {
    const response = await proxy(req(`${ACCESS_COOKIE}=whatever-signed-value`));
    expect(setCookieValue(response, DEMO_TENANT_COOKIE)).toBeNull();
    expect(forwardedRequestHeader(response, DEMO_TENANT_HEADER)).toBeNull();
  });

  it("logs and mints a replacement when the existing cookie fails signature verification", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const response = await proxy(req(`${DEMO_TENANT_COOKIE}=tampered.garbage`));
    expect(error).toHaveBeenCalledWith(expect.stringMatching(/signature verification/i));
    expect(setCookieValue(response, DEMO_TENANT_COOKIE)).toBeTruthy();
  });
});
