---
title: CTO re-evaluation, Pricekeel, one day after PR #69
created: 2026-09-27
updated: 2026-09-27
tags: [review, cto, pricekeel]
status: draft
---

# CTO re-evaluation (read-only, tree 00bd935)

## Status of my five findings

**F1 usage data contract. OPEN, unchanged.** `web/src/lib/salesforce-adapter.ts:17-36`
still has no committed_acv, overage_rate or ramp field. Those live only in
`pricing/schema.py:130-148`, ingest, mapping and generate, and still drive no
decision. `web/src/app/page.tsx:53` still sells "usage or hybrid SaaS". No
"usage evidence: not connected" state exists anywhere in web/src. The vault
already concedes the scope (`vault/Projects/pricekeel-salesforce-workflow-v1.md:133`);
the product surface does not.

**F2 actor identity. PARTIAL.** Tenant isolation is real: per-visitor signed demo
tenant at `web/src/lib/gate.ts:68-82`, tenant-scoped reads in
`pricing/governance.py:165-200`. Person-level identity is not:
`api/routers/crm.py:383,545` still write `"actor_assertion": "self_asserted"`, and
segregation of duties is still a normalized typed-name compare at
`api/routers/crm.py:293-299`. No approver allowlist. PR #61 unmerged, so the tenant
key is still the shared access code itself.

**F3 durable audit write. CLOSED.** `api/routers/crm.py:143-180` fails closed with
503 in prod; the batch path probes once before writing (`:407`).

**F4 evidence_version. CLOSED, and done properly.** `api/routers/crm.py:111-141`
hashes the book content, not just its length, returns decomposable inputs, and
approvals inherit the request-time fingerprint (`:363-370`). Tests at
`tests/test_crm.py:605-703`.

**F5 refetch per click. PARTIAL.** Approve and reject no longer refetch
(`web/src/lib/salesforce-workspace.ts:136-143`). Everything else still pulls the
full book: SOQL `LIMIT 9999` over 730 days (`salesforce-adapter.ts:223-229`),
`cache: "no-store"` (`salesforce-workspace.ts:35`). No persisted book, no sync
timestamp.

## New risk the fixes introduced

1. evidence_version json-dumps and sha256s the entire book per verdict
   (`crm.py:78-93`). Correct, but it compounds F5: the per-click cost is now
   refetch plus full-book hash.
2. `_git_sha()` shells out to git in the request path when no env var is set
   (`crm.py:64-73`). In a container without git it returns "unknown" and two
   builds fingerprint identically. Set PRICEKEEL_GIT_SHA on Render before pilot.
3. Fail-closed is gated on `main._is_prod()` (`crm.py:172`), so the 503 path is
   exercised only by tests, never by daily use.
4. Mixed currency now hard-blocks 422 on the CSV path (`api/main.py:330`) but only
   warns on the Salesforce path (`salesforce-adapter.ts:324`). Two behaviors for
   one defect.
5. Per-visitor demo tenants give decision_log unbounded customer_ref cardinality
   with no retention rule.

## Verdict

Pilot-admissible for an NDA'd design partner on sandbox or scratch-org data,
read-only. Not admissible for real customer data: per-user identity is the last
technical gate, and `web/src/lib/legal.ts:18-19` still renders "[legal entity]".

## Next week, one thing

Per-user authenticated actor identity (magic link) with an approver allowlist,
replacing the typed-name compare, stamping `actor_assertion: "authenticated"`.
That alone converts the audit trail from a demo artifact into evidence.

## Landing page, to a CTO buyer

- Claim: every number names its method and carries a reproducible evidence hash.
- Claim: it fails closed. No durable audit write, no recorded decision.
- Claim: read-only Salesforce, first recommendation in under two weeks, no warehouse project.
- Drop: "usage or hybrid SaaS" as an implied capability until a billing connector
  exists. Say "governs discount on CRM contract values" instead.
