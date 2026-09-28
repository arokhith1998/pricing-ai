# Pricekeel pilot readiness, re-evaluation (customer-success lens), 2026-09-27

Read: prior report (eval-customer-success.md), closure doc (fifteen-agent-evaluation.md),
plus live code on main (00bd935): pricing/ingest.py, pricing/metrics.py, pricing/diagnostic.py,
api/main.py, web/src/app/api/diagnostic/route.ts, web/src/app/sample/page.tsx,
gtm/data-request.md, gtm/personas.md, docs/legal/one-page-mutual-nda-data-addendum.md,
docs/ops/salesforce-integration-runbook.md, neon/schema.sql, docs/ops/funnel-tracker.csv.

## Verified: the five claims

1. **Insufficient data, not $0.** Confirmed, with a nuance. A book under
   `MIN_CLOSED_DEALS = 30` (pricing/ingest.py:36) fails loudly as a SchemaError, which
   api/main.py maps to HTTP 422. A book that clears 30 total but has no band with 15+
   deals gets a 200 response with `excess_basis: "insufficient data"` and a disclosure
   string carrying `band_counts` (pricing/metrics.py:713-754), rendered on the sample page
   next to the segment-aware figure. So "422 with band counts" is literally true only for
   the whole-book floor; the more common thin-segment case is an honest inline disclosure,
   not a rejection. Functionally the outcome is the same: no fabricated leakage number.
2. **Mixed currency blocked.** Confirmed. `CurrencyBlockedError` carries per-currency row
   counts, api/main.py:329-345 maps it to 422 with `detail` and `blockers`, and the web
   proxy (web/src/app/api/diagnostic/route.ts:32-46) forwards both.
3. **gtm/data-request.md currency line.** Confirmed at line 61: explains ISO code
   inference and states a mixed file is blocked, one currency per file or supply FX rate
   and date.
4. **GTM collateral aligned to ICP.** Confirmed for personas.md (updated 2026-09-26, ARR
   band 10-100M, sweet spot 20-60M, matches the Aug 1 assessment). Did not re-check
   outreach-sequence.md or objection-inventory line by line; spot check is consistent.

## Six findings, re-assessed

1. **Pipeline: still zero.** funnel-tracker.csv is still header-only, no rows. Unchanged,
   still critical, and it is the one item on this list that no engineering fix touches.
2. **Salesforce package: still not built.** Runbook still states "the repository does not
   yet contain a Salesforce DX package" as an open release gate. Unchanged, critical, still
   the top bounded engineering blocker.
3. **Legal paper: still not signable.** Same NDA/addendum, same "NOT SIGNABLE" banner,
   entity still a bracketed placeholder pending incorporation. Unchanged, high.
4. **Cross-pilot usage rollup: still absent.** No file or route implements it; it is not on
   the closure list. Unchanged. Low urgency with zero pilots, but it must exist before a
   second design partner, so build it during pilot 1 rather than after.
5. **Evidence floor: structurally improved, still empirically unproven.** The 30-deal and
   100-deal/15-band floors are now enforced everywhere with an honest failure mode instead
   of a silent number. That is a real fix to the risk (no more confident wrong answers on
   thin data) but it does not create volume: the only live org still has far fewer than 500
   closed outcomes. Downgrade from "the diagnostic can lie" to "the diagnostic will refuse
   to answer," which is the correct posture for a CFO-facing tool.
6. **Actor identity: partially closed.** Per-visitor demo tenant, tenant-scoped doc store,
   fail-closed CRM audit writes, and evidence_version landed. But `neon/schema.sql:62`
   still defaults `customer_ref` to the literal `'default'`, and PR #61 (opaque tenant key)
   is still open per the closure doc. Real design-partner data must not land in a schema
   with a shared default tenant bucket. Downgrade from critical to high, not closed.

## Updated verdict

**Conditional, closer, still not yes.** The engineering fixes closed the two things a
skeptical VP Finance would have caught on the first call (a leakage number that does not
tie out, a headline built on data too thin to support it) and closed a real security gap
in the RAG/copilot layer. But the three blockers that stop a real design partner from ever
reaching that call are unchanged: no funnel, no installable Salesforce app, no signable
paper. None of those are code problems the next sprint fixes; they are founder-owned work
that has not moved since yesterday's evaluation.

## Two-week onboarding runbook, first design partner, yes on Monday

Preconditions before Monday: legal paper closed (entity named, counsel-reviewed,
benchmarking-consent clause intact per the 2026-06-11 decision note), PR #61 merged so
`customer_ref` is opaque per tenant, not `'default'`.

**Week 1**
- Mon: Founder sends NDA + data addendum for signature (gtm/data-request.md as the ask
  list). CS lead schedules the data-readiness call.
- Tue: Data-readiness review call against `docs/ops/salesforce-integration-runbook.md` and
  `docs/guides/customer-salesforce-workspace.md`: confirm 500+ closed outcomes, list/booked
  fields, discount policy, policy owner. Blocker risk: partner's Salesforce admin is not on
  the call, or the org is a hybrid of Opportunity and CPQ objects the field dictionary does
  not cover.
- Wed: NDA countersigned. Partner's Salesforce admin installs the Pricekeel ECA. **This is
  the hard blocker**: if the 2GP package still does not exist, the admin cannot install
  anything into their own org, and the whole two-week clock stops here regardless of legal
  status.
- Thu-Fri: OAuth completes, first live extract pulled via the connected app; run through
  `pricing/ingest.py` LoadReport to disclose what was read/dropped before any number is
  shown. Blocker risk: mixed currency (blocked, needs FX rate) or under 30 closed deals
  (422, needs a wider date range from the partner).

**Week 2**
- Mon-Tue: Diagnostic run against `pricing/diagnostic.py` and `pricing/metrics.py`;
  internal review of the segment-aware headline, band_counts, and any insufficient-data
  flags before the customer sees them.
- Wed: Readout call using `gtm/readout-close-script.md`, leading with the load report and
  the "what we would not change" counterweight.
- Thu: Pilot proposal ($15K, 50% credited toward $30-60K annual) sent for signature.
- Fri: If signed, connect the exception loop (`web/src/app/api/exceptions/route.ts`) and
  weekly digest for recurring usage tracking; log the row in `docs/ops/funnel-tracker.csv`.

Biggest single risk to the whole two weeks: the Salesforce package. Everything else on
this runbook is sequenced work; that one is a hard stop if not already shipped.
