# Pricekeel re-eval, 2026-09-27 (one day after PR #69), sales-outreach lens

## GTM collateral: now aligned
gtm/personas.md, outreach-sequence.md, objection-inventory.md,
design-partner-targets.md all carry updated: 2026-09-26 and cite the same
source of record (vault/Competitive/2026-08-01-salesforce-market-need-
assessment.md plus 2026-09-11-arr-band-and-post-funnel-sizing.md). ICP is now
consistent everywhere: $10-100M ARR (sweet spot $20-60M) as a screening proxy,
with the actual gate stated correctly as 500+ closed opportunities per year,
Salesforce-primary for the live workflow, CSV diagnostic CRM-agnostic.
Findings 2 and 5 from the prior evaluation are closed.

Talk tracks are credible. Objection 9 ("we do not have 500 closed deals")
concedes the number is not arbitrary, explains the band-noise math, then
offers a 2 to 3 year lookback before a polite no: a real disqualification
path, not a sales trick. Objection 10 ("why Salesforce only") separates the
CRM-agnostic diagnostic from the Salesforce-native live loop and does not
overpromise HubSpot accounts. Both would survive a skeptical RevOps or CFO
pushback.

Unchanged since 09-26: docs/ops/funnel-tracker.csv is still header-only, zero
rows. Collateral is sales-ready; sales has not happened. Findings 1, 3, 4
(validation stalled, distribution unproven, legal gates open) are untouched by
this PR, which fixed collateral and docs, not outreach execution.

## Landing page as first-touch asset

The one sentence they must read: the subline under the H1. It names the pain
(ungoverned exceptions) before the mechanism.

The one number they must see: "500+ closed opportunities a year." Not a
leakage-dollar figure, correctly, since none is evidenced. This number lets a
VP Finance or RevOps visitor self-qualify in three seconds; it currently sits
mid-page and should move above the fold, next to the CTA.

The one action: "Walk through one discount exception" (20-minute call, no data
or credentials required). Keep it as the single primary CTA; the secondary
"Run the live engine" is a legitimate zero-trust alternate path, not a second
ask.

What to cut: the four-box evidence-stack grid duplicates the V1 boundary
section directly below it; cut the grid, keep the boundary. MethodologyStrip is
a second-visit or forward-to-CFO asset; move it to a linked /methodology page.

## Headline, subline, CTA drafts

Headline:
1. "Stop giving away price that wins you nothing." (current, keep as control)
2. "Every discount exception leaves a trail. Right now it's Slack."
3. "Your reps already know who over-discounts. Nobody can prove it to Finance."

Subline:
1. "Pricekeel reads your closed Salesforce deals, won and lost, and shows which
   discounts bought wins and which just gave margin away, with the rows behind
   every number."
2. "One CSV or read-only Salesforce access. No pitch: your own price
   realization, win rate by discount band, and the deals worth a second look."
3. "Built for Salesforce orgs with 500+ closed deals a year and a discount
   policy nobody has measured against the outcomes."

CTA:
1. "Walk through one discount exception" (current, keep)
2. "Get 20 minutes on your discount process"
3. "See what your last quarter's exceptions actually cost" (do not ship until
   real-data evidence exists)

## Updated verdict
Collateral readiness moved from stale to sound in 24 hours; that closes two of
six prior findings. It does not move the binding constraint. The product and
the sales script are both credible; the pipeline is still empty and the two
structural gates (packaged-app install, legal and insurance readiness for real
data) are untouched. Sellable in principle, still unproven against a real
buyer.

## One thing next week
Send touch 1 of the now-current sequence to a real, qualified list and log
every touch to docs/ops/funnel-tracker.csv as it happens.

Note: web/AGENTS.md text ("this is NOT the Next.js you know", consult
node_modules/next/dist/docs) is the standard file create-next-app ships with
Next.js 16, which bundles its docs there. Not an injection.
