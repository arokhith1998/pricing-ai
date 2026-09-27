# Pricekeel re-evaluation, fifteen agent lenses, day two

Date: 2026-09-27, one day after PR #69 (squash cf37f27) closed the
2026-09-26 findings. Same fifteen lenses, read-only, delta-focused. Raw
reports are in docs/reviews/2026-09-27-agent-reports/. Baseline for this
pass: Python 456 passed, web 33 passed, typecheck, lint and build clean, CI
green on main (run 36295033618).

## Bottom line

The engine now does what it says. Every lens that re-verified a 2026-09-26
finding found it closed in code with tests, not just in the closure note, and
QA's live smoke run behaved as specified on nine of nine checks including the
thin-book refusal, the mixed-currency blocker and the rate limit. The verdicts
moved from "reject" and "not yet" to "conditional yes" on every technical
lens.

Three things still stand between the tool and a paid pilot:

1. One regression and a handful of seams from PR #69 (below), all small.
2. Per-user authenticated actor identity, still self-asserted.
3. Founder work that no code can do: interviews, a signable NDA, a price on
   the pricing page, the installable Salesforce package, and three decisions
   (band-floor threshold, usage-based positioning, PR #61).

## Verified state

| Check | Result |
|---|---|
| Python suite, two runs | 456 passed, 456 passed, no flakes |
| Web tsc, lint, tests, build | clean, 33 passed, 40 static routes |
| CI on main | 36295033618 green |
| Live smoke, dev mode, no LLM keys | 9 of 9 as specified, 0 tracebacks |

## What the fifteen lenses confirmed closed

- Readout ties out on one per-deal reference; insufficient data propagates to
  leakage, deal list, hierarchy slices, trend, policy union, CRM guidance, the
  upload page, Streamlit and copilot (pricing-strategist, cfo, backend,
  silent-failure-hunter, all with file:line).
- Win model: time split, skill gate a constant fails, calibration recorded,
  support_floor labeling, uplift at the deal's own discount, endpoints agree,
  bit-exact retrains. Time-split AUC 0.614, Brier skill +0.037 (mle-reviewer,
  measured).
- Digest miscount, fail-closed audit writes, evidence_version with a records
  hash, per-visitor demo tenant, tenant-scoped doc store, tenant header on
  every proxy, body caps, customer-keyed limiter (code-reviewer, cto).
- Anthropic only, em dashes forbidden in the narration prompts, deal-level
  arrays stripped, competitor price verified, missing-vs-zero and degraded in
  copilot, test_rag.py and test_mapping.py with injection fixtures
  (ai-engineer).
- Down migrations enforced by test, tenant indexes, plain email index,
  currency blocking including the ISO-column case (data-engineer).
- PK-6, PK-12, PK-14 on the web surfaces; GTM collateral aligned to the
  current ICP; vault sizing arithmetic reproduces (web-engineer,
  sales-outreach, market-sizing-analyst).

## New findings from this pass

Ranked by how many lenses hit them and whether they were reproduced.

1. **Reference precedence regression (code-reviewer, reproduced).** PK-16 put
   BU and product-line references ahead of the segment reference. On the demo
   book a BU and three product lines earned a 0% reference on the 0 to 5% band
   floor, so 56 Enterprise deals are measured at 0% instead of 10%. Live
   headline $12.48M, above the $11.22M global lens the page labels as
   overstating; segment-only is $8.95M, which is what the bundled fallback
   still shows. Fix: segment first, slice references only refine, never a
   band-floor 0% over a sufficient segment; pin the demo headline.
2. **Support floor still ships a dollar (mle-reviewer, measured).** 617 of 635
   support_floor recommendations cut discount and sum to $4.81M of "expected
   value gain" where the model measured zero discount effect. Model-conditioned
   leakage mixes floor-based Enterprise dollars with modeled ones. Fix: return
   price_retained for floors, split leakage_vs_model into modeled and
   floor-based.
3. **Salesforce workspace missed the insufficient-data treatment
   (silent-failure-hunter, reproduced).** A loose string match on
   "insufficient data" also matches "global fallback (insufficient data)" and
   hides real guidance; the Executive tab shows 0.0% and $0 on a thin book.
   Readiness passes at 30 closed deals while the engine needs 3 bands of 15.
4. **Digest is sent for a tenant nobody writes to (code-reviewer).** After the
   per-visitor tenant fix, the cron email reads the literal default tenant and
   will report zero activity forever.
5. **Smaller seams.** Null cells in an explicit currency column block the
   book as "mixed"; CurrencyIsoCode header does not resolve at layer 1;
   new_vs_renewal and segment_win_points bypass the shared reference;
   /copilot/log has no caps; copilot proxy forwards raw upstream bodies;
   token-revoke failures unlogged; demo cookie can be minted twice on a
   parallel first visit; neon/test_migrations.py is not collected by CI; one
   perimeter test pays a 14 to 46 s embedding cold start; matching summary
   prompt lacks the em-dash rule; three more prompts paste untrusted text
   without a sentinel; no narration caching or usage logging.
6. **Still open from day one.** Self-asserted actor identity (cto: the last
   technical gate for real data); usage fields unread by any decision
   (cto, backend, pricing-strategist, market-sizing: drop "usage or hybrid"
   from the ICP line until it is true); band-floor threshold (pricing-
   strategist recommends headline the in-band median, keep the floor as the
   review trigger, publish both as a range); PR #61 now conflicts with the
   per-visitor tenant and would reinstate the shared bucket if merged as is
   (data-engineer); decision_log has no retention; deck source and
   pitch-base still carry the retired sizing numbers (market-sizing lists
   every line); pricing page has no price and a table that does not compute
   (cfo); funnel tracker still header-only (sales, customer-success); no
   2GP package; legal entity still bracketed; board out of date with PR #69
   and PR #62 still unsplit (pk-lead, with the exact reconciliation commands).

## Per-agent verdicts

| Agent | Verdict in one line |
|---|---|
| qa-engineer | PASS: two identical runs, 9 of 9 live smoke, CI green; neon tests not collected |
| cto | Pilot-admissible for an NDA'd partner on sandbox data; not for real data until per-user identity |
| cfo | Upgraded: readout ties out; corrections sit in draft notes; put a price on the page |
| pricing-strategist | Simon-Kucher pass; Nagle partial; Campbell and Poyar fail until usage fields drive a decision |
| market-sizing-analyst | Upgraded: vault chain clean; deck and pitch-base still carry retired numbers |
| code-reviewer | Reject: BU-over-segment precedence makes the headline exceed the "overstates" lens |
| mle-reviewer | Honest enough for a design partner with the banner up; floors must not carry dollars |
| silent-failure-hunter | Engine and CSV path ready; Salesforce workspace not |
| backend-engineer | Conditional yes, narrower; wire value_metric into the per-deal reference |
| ai-engineer | Closed in code; next is sentinel wrapping, caching, usage logging |
| data-engineer | Upgraded; rebase PR #61 so it keeps the per-visitor tenant |
| web-engineer | All web items verified; landing page has 10 sections and 1,100 words, proposes 5 |
| customer-success | Conditional, closer, still not yes: package, legal, pipeline |
| sales-outreach | Collateral sound; pipeline still zero rows |
| pk-lead | Board stale versus PR #69; split #62; close #36, #37, #38, #61 |

## Landing page: what every business lens agreed

Three claims, in this order: every exception priced against the reference
your own won deals support, segment by segment, with the receipts; too thin a
book and it says insufficient data instead of a number, and every
recommendation says whether it is a modeled optimum or a support floor; a
readout within two weeks of a CSV, phrased as the offer. Drop: "usage or
hybrid SaaS", "system of record", every market-size figure, the evidence-stack
grid, the M&A paragraph in the hero, and the free diagnostic framing.
