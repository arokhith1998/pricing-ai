---
title: CFO evaluation of Pricekeel, whole-tool review
created: 2026-09-26
updated: 2026-09-26
tags: [cfo, unit-economics, market-sizing, review, pricekeel]
status: draft
---

# CFO evaluation, 2026-09-26

## 1. Verdict

The engineering is more financially honest than the commercial model is. The
diagnostic refuses to invent a recovery rate, labels lens 3 correlational, and
discloses its reference basis per segment. That is audit-grade and rare. The
commercial layer has not caught up. The wedge SAM was correctly revised on
2026-09-11 from $120-215M to $11-29M (Tier A) and $4-11M (Tier B), and nobody has
re-run the SOM against it: the still-active panel note claims 100-250 customers
and $5-15M ARR, which against 350-480 Tier A accounts is 21% to 71% share of the
entire addressable market. That is not a plan. Separately, the live pricing page
carries no price, gives away the highest-COGS deliverable free, and supports the
subscription with three ROI thresholds that are asserted rather than computed,
one of which does not even reconcile with its own arithmetic. Margin is not the
risk people think it is: LLM inference here is narration and column-mapping
fallback at 350 to 1500 max_tokens per call, so cash COGS per customer is
trivial. The drag is founder hours and a free diagnostic. Fix the reference-basis
inconsistency and put a price on the page before the first real CFO sees a
readout.

## 2. Top five findings

**F1. SEVERE. The SOM was never re-derived after the SAM was cut by an order of
magnitude.** `vault/Competitive/2026-06-10-panel-review-tam-sam-som.md:66` is
`status: active` and states SOM of $5-15M ARR at 100-250 customers off a
$120-215M SAM. `vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md:70`
cuts the addressable pool to 350-480 US Tier A accounts. 100 / 415 = 24% share;
250 / 415 = 60% share. Even 20% of Tier A at a $45K midpoint ACV is 83 accounts
and $3.7M ARR, and Tier B alone caps at $4-11M. Recommendation: mark the June
note superseded, restate SOM as 8-12% of Tier A over five years (roughly $1.5M
to $2.5M ARR from the wedge alone), and make the deck say in one sentence that
the wedge cannot fund a Series B and the expansion bridge is the company.

**F2. SEVERE. Four sections of one readout use three different reference bases,
so the document will not tie out.** Headline excess is segment-aware
(`pricing/metrics.py:493-496`). `top_leak_deals` is segment-aware
(`metrics.py:628`). But `defended_vs_investigate` uses the global reference
(`metrics.py:546-548`) and `trend_by_quarter` uses the global reference
(`metrics.py:666`). A CFO will add the investigate deal count to
`deals_above_segment_reference`, find they disagree, and discard the whole PDF.
Recommendation: pass a per-deal threshold into both, keep the global series as a
labeled secondary line, and print a reconciliation footer.

**F3. HIGH. The pricing page has no price, gives away the expensive thing, and
its ROI math is invented.** `web/src/app/pricing/page.tsx:25` makes Diagnostic
free for design partners; `:186-189` and `:395` say only "low five figures". The
$15K pilot and $30-60K ACV appear nowhere public. Worse, the three renewal
thresholds at `:150-168` are asserted: "5 hours per week saved" (5 x 52 x 80 =
$20,800, arithmetic fine, observation zero) and "1 to 2 deals per quarter ...
3 to 5 extra points at $250K ACV = $30K to $50K", which does not compute: 2 deals
per quarter at 5 points of $250K is 8 x $12,500 = $100K, not $50K, and a $250K
ACV deal is not typical of a $10-100M ARR ICP. A company whose thesis is that
list price is fiction is selling without a list price and anchoring the buyer at
zero. Recommendation: publish $15K for the diagnostic, 100% credited to the
pilot; publish the $30-60K band; delete or recompute the threshold table (this is
PK-14 scope).

**F4. HIGH. The quarter-end dollar is the weakest number in the readout and it
sits in the section a CFO will quote.** `metrics.py:571-573` attributes
(QE discount minus rest-of-quarter average discount) x list ACV to timing, with
no control for deal mix, and that figure is then published as a policy lever in
`policy_simulations` (`metrics.py:732`) alongside two reference-based figures. The
three simulated policies also overlap (a deal can be above segment reference, off
policy, and in the QE window) and `diagnostic.py:288-292` prints them stacked with
an upper-bound caveat but no "these do not sum" warning. Recommendation:
size-stratify the QE comparison, and print the union figure with an explicit
non-additive line.

**F5. MEDIUM. Margin framing is defensive in the wrong direction, and the pilot
is not ARR.** `gtm/llama-ventures/pitch-base.md:222` targets blended gross margin
"above roughly 60 percent", which invites a diligence question you do not need to
invite: the software COGS here is near zero. The real drag is the 13-19 founder
hours per prospect and a free diagnostic. Also, a $15K 90-day pilot with 50%
credited is not $15K of ARR: $7,500 is a deferred material right under ASC 606,
year-1 cash is $37.5K to $67.5K against a $45K to $75K list, an effective 10% to
17% year-one discount. Recommendation: target 80%+ on the software line, price
onboarding as a separate non-recurring line, and report pilots as bookings, never
ARR. Note also that `pricing/assist.py:53` still defaults `LLM_PROVIDER` to
"openai" despite PK-5 being marked done, which is a live subprocessor-disclosure
exposure (PK-6).

## 3. Three genuinely good things

1. The product refuses to sell a number it cannot defend. `metrics.py:538` returns
   the defended/investigate split with "no assumed recovery rate", the module
   docstring at `metrics.py:19-23` labels lens 3 correlational, and
   `web/src/app/calculator/page.tsx:53-62` volunteers that the public calculator
   understates and refuses to invent a recovery rate. That discipline is the
   asset.
2. Segment-aware references with a disclosed basis (`metrics.py:345-393`, the
   `_BASIS_FALLBACK` string) fixed a real overstatement and disclosed it in the
   output rather than quietly reducing the headline. Same for the per-value-metric
   cut. This is the behavior that survives a pricing committee.
3. Evidence tiering. `gtm/llama-ventures/traction-update.md` is the single owner
   of traction claims, synthetic funnel rows are quarantined, and the 2026-09-11
   decision cut the company's own SAM by 6x against its own interest. That is the
   strongest governance signal in the repository.

## 4. The one thing next week

Make the readout tie out. One day of work in `pricing/metrics.py`: put
`defended_vs_investigate` and `trend_by_quarter` on the same per-deal segment
reference the headline uses, print a reconciliation line, and mark the policy
simulations non-additive. Two design-partner conversations are live. The first
real CFO to open that PDF will try to tie the numbers to each other before
believing any of them, and today they do not tie.
