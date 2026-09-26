# Pricekeel evaluation: market sizing and category lens (2026-09-26)

## 1. Verdict

The sizing story is in the top decile of pre-seed material I have audited: the
2026-09-11 decision retired the pre-funnel $120M to $215M headline, the deck now
leads with the post-funnel wedge ($11M to $29M Tier A, $4M to $11M Tier B) and
volunteers that it is small, every ACV-derived figure is labeled assumed, and the
expansion bridge is shown as a separate multiplier stack. That is the correct
structure. What remains wrong is arithmetic inside that structure: the funnel
collapse factor, the pre-funnel ACV, and the bridge endpoint do not reproduce from
the numbers printed beside them, and the single most load-bearing figure in the
deck (350 to 480 qualified US accounts) is still an unsourced assumption. Separately,
the product prices a discount percentage, not a usage-based contract structure, so
the ICP claim "usage or hybrid" is a positioning choice the engine does not yet
earn. Fixable in a week. None of it is fabrication; all of it is checkable by a
Series A associate with a calculator.

## 2. Top five findings

**1. The funnel collapse factor contradicts its own table. High.**
`decks/_check-10-market.png` (slide 10) says the gates "collapse it four to six
times" above a table reading 3,000 to 3,600 down to 350 to 480. That is 7.5x to
8.6x on matched endpoints, 6.25x to 10.3x across extremes. Origin:
`vault/Competitive/2026-08-09-two-tier-sizing-crm-agnostic-and-india.md:39`
("collapses it ~4-6x"). Fix: say "roughly 8x" and, better, replace the single step
with per-gate survival rates (500+ closed outcomes, data readiness, policy owner,
champion, CFO buyer).

**2. The pre-funnel row is computed at a different ACV than the rows beneath it.
Medium-high.** `vault/Competitive/2026-06-10-panel-review-tam-sam-som.md:61` derives
$120M to $215M at a $40K to $60K ACV, while the deck's Tier A card and
`gtm/llama-ventures/pitch-base.md:183` use $30K to $60K. At $30K to $60K the
pre-funnel layer is $90M to $216M. Fix: one ACV band across all three rows, or
footnote the difference.

**3. The expansion bridge endpoint is not reproducible. High.**
`gtm/llama-ventures/pitch-base.md:198` and slide 11 claim "15 to 40 times, reaching
$300M to $1B+". The printed stack multiplies to 12x to 36x (2 x 1.5-2 x 2-3 x 2-3),
and 15x on $11M is $165M, not $300M. Only the top end survives. The geography 2x to
3x also conflicts with the company's own global-to-US ratio of roughly 1.7x to 2x
(`2026-06-10-panel-review-tam-sam-som.md:60`). Fix: publish $165M to $1.05B, or
re-derive geography and say which multipliers compound independently.

**4. The engine is discount-percent native, not usage-native. High, product-market.**
`pricing/schema.py:121-134` marks `committed_acv`, `overage_rate` and `ramp_year_*`
optional, and `pricing/model.py:45-47` uses `discount_pct` as the only lever with
`value_metric` as a stratifier. This is exactly the June panel pushback
(`2026-06-10-panel-review-tam-sam-som.md:47-49`). Consequence for sizing: the
"relax the usage-only gate, ~2x" multiplier is not a future unlock, it is available
today at zero build cost, while the UBP differentiation that justifies the wedge is
the unbuilt part. Fix: either move that 2x into the wedge with the gate restated, or
build commit/ramp/overage before Tier A is quoted as usage-native.

**5. Competitive-window facts are one quarter stale, and ICP language still drifts.
Medium.** Adyen/Orb and Salesforce/m3ter both closed 1 July 2026 (verified today),
but `web/src/app/page.tsx:61-64`, `gtm/llama-ventures/pitch-base.md:105-109` and
`vault/Competitive/2026-08-09-metering-landgrab-why-now.md:32-34` still say "agreed
to acquire". The "12-18 months from mid-2026" window (same note, line 44) is now 9
to 15 months and has not been re-dated; the note's own quarterly re-verify is due.
Residual band drift: `gtm/objection-inventory.md:23` says "$15-60M ARR" and
`gtm/design-partner-targets.md:22,127` still admits HubSpot against a Salesforce-gated
Tier B.

## 3. Three genuinely good things

1. `vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md` catches the
   company's own order-of-magnitude error, records that it was stated to an
   investor, and fixes it everywhere. That is the behavior diligence is testing for.
2. Discipline on unvalidated ACV holds end to end: "ASSUMED ACV" on the slide,
   "hypothesis, pre-pilot" at `pitch-base.md:188`, and the no-publish rule at
   `2026-08-01-salesforce-market-need-assessment.md:91-105`.
3. The qualification gates are engineered, not asserted: `pricing/schema.py`
   required fields are the data-readiness bar, `pricing/governance.py:88` makes the
   append-only decision log real, and `gtm/personas.md:159-160` turns away sub-$8M
   and seat-only accounts by name.

## 4. The one thing next week

Instrument the funnel. Take the 18 named US candidates at
`2026-08-09-two-tier-sizing-crm-agnostic-and-india.md:83-85`, measure four gates
each (annual closed-opportunity count, value metric, named policy owner, primary
CRM), and publish the observed survival rate with n. That converts 350 to 480 from
the deck's only unsourced number into a counted sample, and it fixes findings 1 and
2 as a side effect.
