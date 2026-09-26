# Pricekeel data layer eval (read-only)

## 1. Verdict

The data layer is strong for a pre-design-partner product: pricing/schema.py is a genuinely
complete deal contract (commit, overage, two-year ramp, renewal + uplift, COGS, BU/line
hierarchy, list vs net), pricing/generate.py bakes true and non-leaking signal into the
synthetic set, and pricing/ingest.py + mapping.py are the most mature part of the repo, with
a disclosure-first LoadReport and a real adversarial-fixtures test corpus behind them. The
weak spot is neon/: the one migration that exists on main predates the additive/reversible
rule and has no down file, even though the pattern for doing this correctly already exists,
tested, on two unmerged branches. Multi-tenancy is also still a fiction (customer_ref
defaults to 'default' everywhere) with a fix sitting unmerged on fix/tenant-key-opaque.
Nothing here is customer-data-unsafe; the risk is operational (migrations) and correctness
under real multi-currency, multi-tenant data.

## 2. Top 6 findings

1. **[High] No down-migration on main.** `neon/migrations/2026-08-01-salesforce-crm-workflow.sql`
   has no `.down.sql`. The correct pattern (guarded, idempotent, refuses when it would destroy
   data) already exists and is tested on `origin/fix/tenant-key-opaque` at commit `1351d9f`
   ("fix: add down-migration and deploy-then-migrate ordering for CRM rename") and on
   `origin/feat/crm-provider-schema`'s `2026-08-18-crm-provider-generalization.down.sql`.
   Recommendation: backport a down for the 08-01 migration onto main now, before anything else
   lands, using that same DO-block guard style.

2. **[High] Tenant key is not opaque; multi-tenancy is a placeholder.** `neon/schema.sql:47`
   (`customer_ref text not null default 'default'`) and every call site in
   `pricing/governance.py` (e.g. lines 112, 169, 223, 269) default to the literal string
   `'default'`. There is no tenant table, no opaque key generation, and no guard against one
   tenant guessing another's `customer_ref`. This is already known and partially fixed on
   `origin/fix/tenant-key-opaque` (commit `6a36d3d`, "give tenants an opaque key instead of
   reusing the access code") but that branch is unmerged. Recommendation: land that branch
   before onboarding a second real design partner; today two customers would share a
   `decision_log` row space keyed by a guessable string.

3. **[Medium-High] No currency field in the canonical schema; mixed currency is detected, not
   handled.** `pricing/schema.py` FIELDS has no `currency` column at all. `pricing/ingest.py`
   `_scan_currencies` (line 477) only raises a warning string when `$`/`€`/`£`/`¥` both appear;
   `_money_to_float` (line 395) strips the symbol and returns a bare float either way. Verified
   directly: running `ingest_verbose` on `data/synthetic/round3-fixtures/mixed_currency.csv`
   (300 rows, genuinely mixes `$` and `€`) parses every row to a float and only emits
   `WARNING: mixed currency symbols ... totals may combine currencies`; the $-weighted totals
   in `pricing/metrics.py` then silently sum euros and dollars as one number. Fine for a demo
   fixture, a real problem for the first EMEA design partner. Recommendation: add an optional
   `currency` field to schema.py (ISO code, default USD) and either normalize with a stated
   FX date or hard-fail instead of warn-and-sum.

4. **[Medium] decision_log has no tenant-scoped index.** `neon/schema.sql:59` indexes
   `(kind, created_at desc)` only. Every tenant-scoped read in `pricing/governance.py`
   (`clauses = ["customer_ref = %s", ...]`, lines 178-179, 231-232) filters on `customer_ref`
   first, which is not part of any index, so this scans the full table as tenant count and row
   count grow. Cheap to fix now, expensive to notice later. Recommendation:
   `create index if not exists decision_log_tenant_kind_created_idx on decision_log
   (customer_ref, kind, created_at desc);` as its own additive migration.

5. **[Medium] leads table has no de-dup or uniqueness.** `neon/schema.sql:9-24`: `email` has no
   unique constraint, `access_codes.lead_id` FK has no supporting index. A resubmitted form
   (retry after a slow response, double-click) creates a second full lead row with no
   collision handling, unlike the careful duplicate/conflict logic pricing/ingest.py applies to
   deal CSVs (`_dedupe`, lines 297-316). Recommendation: add a unique index on
   `lower(email)` (or `(lower(email), company)` if the same person can legitimately re-submit
   for a different company) plus an index on `access_codes(lead_id)`.

6. **[Low-Medium] Ramp schema stops at year 2 with no documented year-3 convention.**
   `pricing/schema.py:128-134` defines `ramp_year_1_acv`/`ramp_year_2_acv` only, but
   `term_months` (line 103) allows 36-month contracts and `pricing/generate.py:140` treats
   `term >= 24` as "multiyear" for ramp purposes. Year 3 of a 36-month ramped deal is implicitly
   `booked_acv` (steady state) with no field or docstring saying so. A real 3-year-ramp CRM
   export has nowhere to put a distinct year-3 figure. Recommendation: either document the
   steady-state convention explicitly in the field description or add `ramp_year_3_acv` before
   the first prospect with true 3-year ramps arrives.

## 3. Three good things

- `pricing/mapping.py` and `pricing/ingest.py` are senior-level defensive engineering: the
  four-layer header mapper refuses to claim optional fields below high confidence (the
  documented "Forecast Category -> product_family" anti-pattern), and `LoadReport` turns every
  silent-corruption risk (mixed currency, ambiguous day/month order, exact-duplicate rows,
  id conflicts, open-pipeline rows) into a visible line instead of a wrong number. Backed by a
  real adversarial-fixtures suite (`data/synthetic/adversarial-fixtures/`,
  `round3-fixtures/`) rather than happy-path-only tests.
- `pricing/generate.py` bakes a true, discoverable leakage story (quarter-end pressure, per-rep
  discount discipline, a saturating win curve, a deliberate governance gap) without leaking it
  into the model: `pricing/model.py` explicitly excludes `booked_acv`, `price_realization`,
  `discount_amount`, `off_policy`, and `cycle_days` from features, with a documented reason.
  Two independent RNG streams (`seed`, `seed+1`, `seed+2`) keep the optional
  hierarchy/UBP/cost columns from perturbing the pinned core dataset.
- The unmerged branches (`fix/tenant-key-opaque`, `feat/crm-provider-schema`) show the migration
  discipline this repo is capable of: the down-migration for the CRM provider rename refuses to
  run (raises and aborts the transaction) rather than silently destroying HubSpot rows if a
  second provider exists, and documents deploy order in a runbook. That is the reference the
  08-01 migration on main should be brought up to.

## 4. One thing to fix next week

Write and test the down-migration for `2026-08-01-salesforce-crm-workflow.sql` on main, using
the guarded, idempotent pattern already proven on `fix/tenant-key-opaque` (commit `1351d9f`).
It is the one rule violation on the branch everyone else builds on top of, and every day it
stays unfixed, the next migration that lands on main inherits the same gap.
