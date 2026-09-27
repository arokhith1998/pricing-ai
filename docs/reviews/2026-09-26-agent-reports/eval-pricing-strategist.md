# Pricekeel methodology evaluation: pricing-strategist lens

## 1. Verdict

The methodology is more honest than most commercial pricing tools and still not
safe to put in front of a Head of Pricing. The disclosure layer is genuinely
strong: basis columns, receipts per finding, a labeled method on every verdict,
a blocker instead of a confident zero when list price is unmapped. The core
number is where it breaks. "Excess vs reference" is built on a win-rate
saturation band, which the copy calls a Nagle reference price and which is not
one (Nagle's reference price is the buyer's anchor, derived from EVC; nothing in
the repo computes EVC or any willingness-to-pay input, so list price is an
unvalidated anchor and every leakage dollar inherits that). Three mechanical
issues then push the headline in one direction, upward: the threshold is the
band floor, the sparse-data path collapses the reference to zero, and the public
page quotes the lens the engine itself disowns. On usage-based pricing the
product is currently a seat-logic engine with a UBP schema bolted on: commit,
ramp, and overage columns exist in `pricing/schema.py` and are read by nothing
that makes a decision. Positioning drift is largely resolved on the landing page
and re-emerges inside the app.

## 2. Top five findings

**F1. Sparse books silently produce a 0 percent reference, so all discount
reads as leakage. Severity: critical.**
`pricing/metrics.py:298` `stats = _band_stats(min_deals) or _band_stats(1)`
drops the 15-deal floor entirely when no band clears it. The selection rule at
`metrics.py:315-317` accepts the cheapest band whose mean clears the peak band's
lower CI bound; with 2 to 5 deals per band that bound collapses, so "0-5%"
always qualifies and `reference_threshold` becomes 0.0. `pricing/crm.py:228`
admits any book with 30 usable closed deals. Segments are gated at 100 deals and
3 bands (`metrics.py:53-54`), but every thin segment falls back to the global
reference, which has no gate at all. Framework: Simon, a price-response function
needs price variation before it has a shape. Fix: return an explicit
`insufficient_data` reference, suppress the excess headline and the dollar
figures behind it, and show band counts instead.

**F2. The public headline uses the lens the engine disowns. Severity: high.**
`web/src/app/sample/page.tsx:146` and `:292` and
`web/src/components/UploadClient.tsx:109` render
`excess_vs_reference_won`. `pricing/metrics.py:503-509` and
`pricing/diagnostic.py:147-150` state the segment-aware figure "is the one to
use" and that the global lens overstates. On the bundled sample that is
$11.2M versus $8.95M (`web/src/data/sample-fallback.json:63,92`), a 25 percent
overstatement on the number in the lead gate. Framework: Simon-Kucher discount
governance, a governance vendor cannot ship its own weaker lens as the hook.
Fix: point the card and the gate at `excess_vs_segment_reference_won`, keep the
global as a secondary line.

**F3. The reference threshold is the band floor, so discount inside the winning
band is counted as leakage. Severity: high.**
`metrics.py:320` sets `reference_threshold = edges[reference_band]`, the lower
edge. A 5-10% band win point yields a 5 percent threshold, so a deal at 7
percent contributes 2 points of "excess" (`metrics.py:486`) and is bucketed
"investigate" (`metrics.py:548`). `tests/test_segment_reference.py:91-96`
enshrines this: 68 MM deals sitting at the MM win point are charged excess. The
bias is up to the band width on every won deal. Framework: Nagle, a reference is
a level, not an open interval below it. Fix: use the observed median discount
inside the reference band, or report a floor-to-ceiling range.

**F4. The monotone win-curve constraint is absent from `pricing/model.py` on
this branch. Severity: high.**
`docs/agents/PROJECT_STATE.md:36` marks PK-15 DONE and
`vault/Decisions/2026-09-11-win-model-monotone-in-discount.md:21-26` records the
constraint as shipped, yet `_PARAMS` at `pricing/model.py:52-56` carries no
`monotone_constraints` and the docstring states none. Per that same note, the
unconstrained model produced about 150 of 300 recommendations saying "cut the
discount and win more." `recommend_discount` (`model.py:137`) and
`governance.exception_verdict` both ride that curve. Suspect the recorded
torn-write corruption. Fix: verify against `main`, restore, and add a CI
assertion on the booster's own params.

**F5. Commit, ramp, and overage are schema decoration. Severity: high for a UBP
wedge.**
`schema.py:121-134` defines `committed_acv`, `overage_rate`, `ramp_year_1_acv`;
grep shows no reference in `metrics.py`, `model.py`, `crm.py`, `governance.py`
or `copilot.py`. `value_metric_reference_table` (`metrics.py:396`) is computed
and surfaced (`diagnostic.py:51`) but feeds neither `leakage()` nor
`_per_deal_reference` (`metrics.py:451`), so the headline still pools seat and
consumption discounts inside a segment. The landing page sells "usage or hybrid
SaaS" (`web/src/app/page.tsx:53`) while disclosing the gap at `:57`. Framework:
Campbell, the value metric is the whole game; Poyar, hybrid is the default. Fix:
make the per-deal reference a segment by value-metric cell, and give the
exception verdict a structure branch: commit step-up, ramp schedule, or overage
rate as alternatives to a rate cut.

Watch also: `copilot.py:219,258,397,439` applies 40, 50, 50 and 20 percent
recoverable shares to overlapping dollars from the same won deals and returns
them in one impact-ranked list. A CFO will add them. Say they are not additive.

## 3. Three genuinely good things

1. Disclosure as a first-class output. The basis column ("own win point" versus
   "global fallback (insufficient data)"), the load report before any
   conclusion, and the receipts functions (`trade_or_give_deals`,
   `quarter_end_deals`, `packaging_signal_deals`) make an aggregate claim
   auditable deal by deal. This is explainability over accuracy done properly.
2. `defended_vs_investigate` (`metrics.py:519`). Telling sales what its
   discounting earned, not only what it leaked, is the thing that keeps a
   deployment alive past week three. Very few vendors do this.
3. Refusing to compute. `_guard_degenerate_list` blocks onboarding rather than
   reporting a confident zero discount, and `evidence_source: band_guardrail`
   versus `method: modeled_ev_curve` stops demo-grade math being passed off as
   live. That discipline is the moat, more than any model.

## 4. The one thing next week

Fix the headline number end to end, in one change: gate the global reference on
the same sufficiency bar the segments already use and return an explicit
insufficient-data state, move the threshold off the band floor, and re-point
every public surface at the segment-aware figure. Then re-run the sample and
update the deck and landing figures. One number, defensible, everywhere.
