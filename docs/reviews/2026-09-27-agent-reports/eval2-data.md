# Pricekeel data layer, re-evaluation (2026-09-27, read-only, tree 00bd935)

## 1. Verified: the 09-26 findings are closed

- **Every migration has a down.** `neon/migrations/` holds two pairs: `2026-08-01-salesforce-crm-workflow.sql` + `.down.sql` (guarded, refuses when any row exists, deploy order documented at down:31-40) and `2026-09-26-tenant-scoped-indexes.sql` + `.down.sql`. `neon/test_migrations.py:39-46` fails the suite on any up without a down, `:49-56` on orphaned downs, `:59-73` on a missing `begin;`/`commit;`, `:31-34` rejects a vacuous empty directory.
- **Tenant-scoped indexes.** `neon/migrations/2026-09-26-tenant-scoped-indexes.sql:43-50` adds `decision_log (customer_ref, kind, created_at desc)`, `access_codes (lead_id)`, `leads (lower(email))`; mirrored in `neon/schema.sql:82-83, 48-49, 33-34`. The old `(kind, created_at)` index is kept for `/digest`.
- **Plain, not unique, email index.** `neon/schema.sql:26-32` and the migration header (lines 16-28): `saveLead` does a bare INSERT with no ON CONFLICT, so a unique index would fail the migration on existing duplicates and then 500 every form retry. `test_migrations.py:87-96` pins non-uniqueness in both files.
- **Currency.** `pricing/schema.py:117-125` adds optional ISO `currency`, default USD. `pricing/ingest.py:153-165` defines `CurrencyBlockedError` carrying the partial LoadReport. `ingest.py:758-761` folds an explicit `currency` column into the per-row codes before the mixed check, so a CurrencyIsoCode-style export with no symbols is blocked (`:761-775`), and missing fx rates still block (`:776-784`). Covered by `tests/test_ingest.py:210-226` and `tests/test_api_perimeter.py:387` (422, not 500).
- **Ramp year 3.** `pricing/schema.py:141-150` documents the steady-state convention: year 3+ equals `booked_acv`.
- **Generator.** `pricing/generate.py:326-329` assigns `currency = "USD"` as a constant after the RNG loop (no draws consumed); UBP columns use stream `seed+2` (`:123-130`). `data/synthetic/deals.csv` last changed at 9fdf6e8, untouched by #69.

## 2. What remains

**PR #61 vs the per-visitor demo tenant: yes, they conflict, textually and semantically.** `git merge-tree main origin/fix/tenant-key-opaque` reports CONFLICT in `web/src/lib/gate.ts`, `neon/schema.sql`, and `SalesforceWorkspace.tsx`. Worse, #61's `customerRef()` returns `DEFAULT_TENANT_REF` for every lead-only visitor, which reinstates the shared "default" bucket that main's `gate.ts:70-83` (`demo:<uuid>`) fixed. The correct merge keeps both: access code resolves to opaque `tenant_ref`, otherwise `demo:<uuid>`. #61 is also stacked on `feat/crm-provider-schema` (crm_connections rename), so it is a two-branch rebase, not a button.

**decision_log growth and retention: none exists.** No retention/prune/purge anywhere in the repo. Each new visitor mints a `demo:<uuid>` tenant with a one-year cookie (`auth.ts:48`); rows for a lost cookie are unreachable forever. The new index makes reads scale; the table still grows unbounded with anonymous demo rows plus `payload jsonb`. Needs a proposed (not run) retention migration: e.g. delete `customer_ref like 'demo:%'` older than 90 days on a schedule, design-partner rows retained indefinitely.

**Salesforce readiness, honest answer: schema yes, mapper and generator not quite.**
- `pricing/mapping.py:160-162` synonyms do not resolve the literal header `CurrencyIsoCode` (`normalize()` yields `currencyisocode`, no match; verified with a python snippet). Only a column already called `currency`/`CCY` hits layer 1. Add `currencyisocode` and `currency iso code` synonyms; one-line fix, one test.
- Multi-currency: blocked by default, normalized only with `PRICEKEEL_FX_RATES` and a rate date. Consistent with the runbook's "one currency for V1" (`docs/ops/salesforce-integration-runbook.md:135, 198`).
- Multi-year ramps: `generate.py:153-156` draws year 2 at 1.00 to 1.25x `booked_acv`, contradicting the documented convention that the ramp climbs *to* `booked_acv`. Also, a stock Opportunity export carries no ramp schedule (it lives on line-item schedules or the contract), so expect blanks, not a year-3 problem.

## 3. Verdict

Upgraded. The one rule violation on main is gone and enforced structurally; currency went from warn-and-sum to block-or-normalize with the ISO-column case covered. Remaining: merge risk (#61), an unbounded append-only table, two small schema seams (CurrencyIsoCode synonym, generator ramp mismatch). Nothing customer-data-unsafe.

## 4. The one thing next week

Rebase PR #61 onto main and resolve `gate.ts` as: verified access code -> opaque `tenant_ref`, else `demo:<uuid>`. It is the offboarding-defect fix (revoke then disconnect leaves a live Salesforce refresh token) and it drifts further from main every week.
