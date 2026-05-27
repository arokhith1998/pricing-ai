# Pricekeel Buyer Funnel (Phase 2.5) — design doc

Status: approved to build, 2026-05-26. Owner: founding engineer.
Builds on `nextjs-ui.md` (M0–M3 shipped). Decisions confirmed with the founder.

## Goal

Turn the demo into a self-serve buyer funnel that (a) pitches the problem, (b)
lets a prospect feel the value on sample data, (c) captures a qualified lead at
the moment of value, and (d) gates "run it on your own data" behind an
access code issued after contact / NDA.

## Funnel (two-tier, value-first)

```
/ (landing pitch + stats)
  ├─ "Try the sample"
  │     → teaser results (headline + blurred detail)         [public]
  │     → lead form (name, company, role/title, role function, company email)
  │     → full sample Diagnostic + Guidance                  [lead cookie]
  └─ "Run it on your data"
        → show the data template + upload CSV
        → OR "request an NDA" (contact)
        → access code                                        [code cookie]
        → their own Diagnostic + Guidance
```

Rationale: the free sample is the outreach wedge, so it stays impressive. We
capture the lead at the upgrade moment, not before value. The harder gate
(access code) sits only on the prospect's own data + deepest intel.

## Gating model (replaces the all-or-nothing M3 gate)

`proxy.ts` enforces two cookies instead of one global lock:
- `pk_lead` — set after a valid lead form submit. Unlocks the **full sample**
  (`/sample/*` beyond the teaser).
- `pk_access` — set after a valid access code. Unlocks **/upload** (own data).

Public: `/`, the teaser, `/login`, `/api/lead`, `/api/auth`, static assets.
Fail closed in production stays (see `lib/auth.ts:gateActive`).

## Lead capture

Fields: name, company, role/title, role function, **company email only**
(reject free domains: gmail/outlook/yahoo/icloud/proton/…). Stored, then a
`pk_lead` cookie is set. No value is shown before the form on the "full sample"
path, but the teaser (headline numbers, blurred specifics) is shown before it
to earn the submit.

## Access codes

Per-prospect, issued after contact/NDA. Generated server-side, tracked, and
revocable. Stored in Postgres (Supabase), not a shared secret.

Generate: a URL-safe random token (≥16 bytes). Issue one per prospect, record
who and an expiry. A prospect enters it on `/upload`; we validate against the
table and set `pk_access`.

## Data layer (Supabase / Postgres)

```sql
leads(id, name, company, email, role_title, role_function, created_at, ip)
access_codes(code PK, issued_to, lead_id FK, expires_at, used_at, revoked)
```

A thin `lib/store.ts` interface with two implementations:
- **Supabase** when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set (prod).
- **Dev fallback** (in-memory + console) when they are not, so local build and
  verify are not blocked. Access codes fall back to a `PRICEKEEL_ACCESS_CODES`
  env list in dev.

## Upload + template

Surface the canonical template from `pricing/schema.py`: 10 required columns
(`opportunity_id, account_name, outcome, created_date, close_date, segment,
product_tier, value_metric, list_acv, booked_acv`) plus optional enrichers.
Offer a downloadable sample CSV. Upload calls the existing `POST /diagnostic`.

## Trust / data handling (non-negotiable for real uploads)

Uploaded data is processed and **not retained**: the API must read it, compute,
and delete the temp file immediately (today it leaves a temp file behind — fix).
State plainly on the page: processed in memory, not stored, under NDA. This is
the top conversion blocker, ahead of any feature.

## Explicitly deferred to Phase 3 (separate design)

"Connect Salesforce → analyze all clients' special pricing agreements / fixed
discounts → margin & revenue gaps" is a **different product on different data**:
active contracts / entitlements (contracted vs. list price, renewal dates,
committed vs. actual usage), not closed won/lost opportunities. It needs a new
schema, a new metric family (renewal/expansion leakage, price-floor violations,
uplift gaps), and connectors. CSV-from-Salesforce first; native OAuth later.
Will get its own design doc before any build.

## Open dependencies

- Founder provisions a Supabase project and sets `SUPABASE_URL` +
  `SUPABASE_SERVICE_ROLE_KEY` (prod). Local dev uses the fallback.
- Benchmarks ("how you compare to peers") are a future locked feature; seed with
  public operator benchmarks (Poyar/Campbell), labeled, until a base exists.
