import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { devTenantRef, resolveTenantRef } from "@/lib/store";

// Regression tests for the access-code overload fixed on 2026-08-22.
//
// customerRef() used to return the verified access code itself as the tenant
// key, so the code was simultaneously the emailed credential, the primary key
// in crm_connections, the partition key in decision_log, and the
// X-Pricekeel-Customer header. Rotating a code orphaned that customer's CRM
// tokens, and the runbook's offboarding order (revoke, then disconnect) left a
// live refresh token at the CRM with no way to revoke it.
//
// These tests pin the property that actually matters: the tenant key is never
// the credential.

const CODE = "try-pricekeel";

describe("devTenantRef", () => {
  it("is deterministic across calls, so a restart keeps the same tenant", () => {
    expect(devTenantRef(CODE)).toBe(devTenantRef(CODE));
  });

  it("never leaks the access code it was derived from", () => {
    const ref = devTenantRef(CODE);
    expect(ref).not.toBe(CODE);
    expect(ref).not.toContain(CODE);
  });

  it("separates tenants that differ by a single character", () => {
    expect(devTenantRef("partner-acme")).not.toBe(devTenantRef("partner-acmf"));
  });

  it("is a fixed-width opaque hex id", () => {
    expect(devTenantRef(CODE)).toMatch(/^[0-9a-f]{32}$/);
  });
});

describe("resolveTenantRef (dev fallback, no DATABASE_URL)", () => {
  const previous = process.env.PRICEKEEL_ACCESS_CODES;

  beforeEach(() => {
    process.env.PRICEKEEL_ACCESS_CODES = "try-pricekeel, partner-acme";
  });

  afterEach(() => {
    if (previous === undefined) delete process.env.PRICEKEEL_ACCESS_CODES;
    else process.env.PRICEKEEL_ACCESS_CODES = previous;
  });

  it("returns an opaque ref for a listed code, and NOT the code itself", async () => {
    const ref = await resolveTenantRef(CODE);
    expect(ref).not.toBeNull();
    expect(ref).not.toBe(CODE);
    expect(ref).toBe(devTenantRef(CODE));
  });

  it("tolerates surrounding whitespace in the env list", async () => {
    expect(await resolveTenantRef("partner-acme")).toBe(devTenantRef("partner-acme"));
  });

  it("returns null for an unknown code rather than inventing a tenant", async () => {
    expect(await resolveTenantRef("not-a-real-code")).toBeNull();
  });

  it("returns null for the empty string", async () => {
    expect(await resolveTenantRef("")).toBeNull();
  });

  it("gives two different codes two different tenants", async () => {
    const a = await resolveTenantRef(CODE);
    const b = await resolveTenantRef("partner-acme");
    expect(a).not.toBe(b);
  });
});
