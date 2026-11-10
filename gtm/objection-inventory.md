---
title: 'Objection inventory: talk tracks for the ten objections we will actually hear'
created: 2026-06-11
updated: 2026-11-10
tags: [gtm, sales, objections, talk-tracks]
status: active
---

# Objection inventory

The ten objections a VP RevOps, Head of Pricing, CFO, or IT reviewer will actually raise,
with honest answers. House rules: never overclaim, never fake social proof, concede what is
true before answering, and say our own caveats before they find them. The caveats are the
product.

**Current ICP, used in every answer below.** B2B SaaS, **$10M to $100M ARR** screening band
(sweet spot $20M to $60M), usage-based or hybrid pricing, **Salesforce-first**, and at least
**500 closed opportunities a year**. ARR is only the screening proxy; the closed-deal count
is the actual gate. Sources: `vault/Competitive/2026-08-01-salesforce-market-need-assessment.md`
(lines 61-74) and `vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md`. Any
number in this file that disagrees with those two is a bug, not a variant.

## Summary table

| # | Objection | Core of the answer | Supporting asset |
|---|---|---|---|
| 1 | "We can do this in Excel" | You can pivot the wons; the win-rate-by-band analysis needs lost deals and a calibrated reference, and the diagnostic is free, so Excel verifying it costs you 30 minutes | Sample readout at pricekeel.com/sample |
| 2 | "Our data is too sensitive" | Zero-trust path exists: /upload runs in memory, nothing stored, founder never sees it; or mutual NDA with 30-day deletion certification | pricekeel.com/upload · NDA template · security one-pager |
| 3 | "ChatGPT can do this" | The numbers come from a deterministic, auditable engine; the LLM is confined to narration and never computes a figure | Methodology section of the sample readout |
| 4 | "Why not Pricefx / Vendavo" | Different problem and different decade of company; they are enterprise CPQ-adjacent suites for $100M+ orgs, this is a diagnostic plus monitoring cadence for $10-100M ARR usage-based and hybrid teams | gtm/personas.md anti-persona section |
| 5 | "You have no customers" | True, and the terms price it in: free diagnostic, capped design-partner cohort of 3, no auto-renewal, fee structure that lets you exit | Design-partner terms in the pilot agreement |
| 6 | "You're one person" | True; the engine is deterministic and tested, scope is deliberately narrow, WIP is capped at 2 concurrent diagnostics so every readout gets full attention, and the NDA carries the deletion and breach commitments regardless of headcount | Security one-pager · NDA |
| 7 | "Is this just a one-time scan?" | The diagnostic is one-time and free; the product is the monthly cadence the $15K pilot stands up: live readouts, decision log, policy monitoring | Readout close script (offer section) · pricing page |
| 8 | "Our CRM export is a mess" | Expected and handled: the ingest maps messy headers, drops dupes, excludes open deals, and discloses every step in writing before any conclusion | gtm/data-request.md · LoadReport section of any readout |
| 9 | "We don't have 500 closed deals a year" | Honest disqualifier, not a negotiation: below that the band-level win rates are noise. We say so and hand back a smaller, clearly-labeled read rather than a confident wrong one | The 30-outcome readiness threshold in the product · gtm/personas.md anti-personas |
| 10 | "Why Salesforce only, and why now?" | The diagnostic is CRM-agnostic today via CSV; only the live in-CRM workflow is Salesforce-native, because depth in one CRM beats a thin layer over two | vault/Decisions/2026-08-01-salesforce-first-crm-workflow.md · gtm/data-request.md |

## Talk tracks

### 1. "We can do this in Excel"

You can get partway there, and you should: realization by quarter is a pivot table. What
Excel will not give you is the win-rate curve by discount band, because that requires your
closed-lost deals next to your closed-won ones, and almost nobody exports the losses. The
band analysis is what separates discounts that buy wins from discounts that give margin
away. And since the diagnostic is free, the cheapest way to prove Excel was enough is to
let me run it and check my number against yours.

Supporting asset: the sample readout at pricekeel.com/sample, which shows the band-level
output Excel does not produce.

### 2. "Our data is too sensitive"

There are two paths and you pick the trust level. The zero-trust path: pricekeel.com/upload
processes your CSV in memory, stores nothing, and I never see the file or the results;
if the number is boring you close the tab and we are done. The founder-run path adds a
mutual NDA before anything is sent, deletion within 30 days with written certification,
and no PII needed: account and opportunity-level fields only, reps as internal IDs.

Supporting assets: pricekeel.com/upload, the NDA at
`docs/legal/one-page-mutual-nda-data-addendum.md`, [[security-one-pager]].

### 3. "ChatGPT can do this"

Paste your CSV into a chatbot and you will get numbers that look right and cannot be
audited, which is exactly the property a CFO will not accept. Here, every figure comes
from a deterministic engine with a test suite: the same file produces the same number every
time, and each finding ships with the rows behind it. The LLM is confined to narrating
results it is handed; it never computes a figure. If a number is wrong, we can trace why,
which is the difference between an analysis and an artifact you can take to finance.

Supporting asset: the methodology and receipts sections of the sample readout.

### 4. "Why not Pricefx or Vendavo?"

If you are a $300M enterprise running CPQ across thousands of SKUs, you should look at
them; that is their market and they are good at it. They are six-to-twelve-month
implementations priced accordingly, built around seat and unit pricing. This is the
opposite shape: a free diagnostic from one CSV, built for usage-based and hybrid models at
$10M to $100M ARR with enough closed-deal volume to measure, where the question is discount
governance, not configure-price-quote. If the diagnostic finds nothing, you have spent 30
minutes finding that out instead of a six-figure evaluation.

Supporting asset: the anti-persona section of [[personas]] (we tell prospects above $100M
seat-only to go there; saying so builds credibility here).

### 5. "You have no customers"

Correct, and I will not pretend otherwise with logos or vague "teams we work with." The
terms are designed for exactly this stage: the diagnostic is free, the design-partner
cohort is capped at 3 so each one gets founder-level attention, the pilot has no
auto-renewal, and half the pilot fee credits to the annual so the early risk is priced in.
You are not buying a track record; you are buying a free, auditable read on your own book,
and the receipts either hold up or they do not.

Supporting asset: the design-partner terms in the pilot agreement; the cap is stated, not
implied.

### 6. "You're one person"

True today: entity formation and counsel review are in progress and I will not sign
anything until they are done. Three things make one person workable rather than a risk you
absorb. The analysis is a deterministic, tested engine, not artisanal spreadsheet work, so
quality does not depend on my energy that week. Scope is deliberately narrow: I cap work in
progress at 2 concurrent diagnostics, which is why readout dates are commitments rather
than hopes. And the NDA's deletion certification and 72-hour breach notice bind regardless
of company size. What you lose with one person is redundancy; what you get is that the
person who built the method runs your data.

Supporting assets: [[security-one-pager]] (states the solo-founder and pre-SOC2 posture
plainly), the NDA.

### 7. "Is this just a one-time scan?"

The free diagnostic is one-time, deliberately: it is the proof, not the product. The
product is the cadence the pilot stands up: ninety days, $15K at signature, a monthly
readout on your live closed deals within five business days of validated intake, a decision
log that becomes your audit trail of which pricing calls worked, and threshold alerts
between readouts. After the pilot, the annual subscription is $30K-60K a year scaled on
deal volume, and half the pilot fee credits to it if you sign within the pilot window. The
scan tells you where the leak was; the cadence is what stops the next one.

Supporting asset: the offer section of [[readout-close-script]]; the pricing page once
copy is reconciled.

### 8. "Our CRM export is a mess"

Every CRM export is, and the ingest is built for it. Duplicate rows from re-exports get
dropped, open deals left in by mistake get excluded and itemized, currency and encoding
are detected, headers are mapped from your names to ours, and columns we cannot
confidently map are ignored and listed rather than guessed. The first section of every
readout is "what we read from your file": row counts, exclusions, blank fields, so you can
verify the intake before reading a single conclusion. You do not need to clean anything;
send the natural export and a one-line note on which amount field is which.

Supporting assets: [[data-request]] (the 10-column list and export cheat-sheet), the
LoadReport section of any readout.

### 9. "We don't have 500 closed deals a year"

This is the one objection where the right answer is often "then we are not a fit yet," and
I would rather say it in the first call than in the readout.

Concede first: 500 closed opportunities a year is not a sales target we invented to sound
selective. It is the point where win rate by discount band stops being noise. Split your
book into five discount bands and you need enough wins *and* losses inside each band for
the difference between them to mean anything. At 150 deals a year you get bands of thirty,
half of them losses, and a single unusual quarter moves the curve. I will not hand a CFO a
confident number built on that.

Then give them the three honest paths:

1. **Look back further.** The gate is closed outcomes in the dataset, not per calendar
   year. Two or three years of history from a 200-deal-a-year company clears the bar, as
   long as your pricing did not change fundamentally in the middle of it. Most companies
   have this and do not think to offer it.
2. **Take the narrower read.** If the volume genuinely is not there, the diagnostic still
   runs realization, policy conformance and quarter-end behaviour, and it will print
   exactly which sections it suppressed and why. The product enforces this itself: it
   holds analysis behind a minimum-outcomes threshold rather than rendering a chart on
   twelve rows. You get a smaller true answer instead of a bigger invented one.
3. **Come back.** If you are at 200 deals and growing, say so and I will follow up when
   the volume is there. I would rather have the right conversation in a year than the
   wrong one now.

What never happens: I do not lower the bar to win a logo. The whole pitch is that the
number survives a skeptical CFO, and a band curve on thin data does not.

Supporting assets: the readiness threshold enforced in the product, the anti-persona table
in [[personas]], [[data-request]] for the lookback-period ask.

### 10. "Why Salesforce only, and why now?"

Two questions hiding in one, and they get different answers.

**"Only" is not quite right.** The diagnostic is CRM-agnostic: it runs on a CSV of closed
opportunities from any CRM, and that is the path into every first conversation. What is
Salesforce-native is the *live* workflow: reading opportunities over OAuth, writing the
decision back as context on the record, and reconciling the outcome. So if you are on
HubSpot you can get the full diagnostic and the readout today; what you cannot get yet is
the in-CRM loop.

**Why Salesforce first.** Depth in one CRM beats a thin layer over two. The value of this
product is that the decision gets recorded where the deal lives, with the evidence
attached, and survives an audit. That requires real integration work per CRM: object
model, permissions, packaging, install path. Doing it properly once, in the CRM most of
our qualified pool already runs, is a deliberate sequencing choice, and it is written down
as a decision rather than a drift: `vault/Decisions/2026-08-01-salesforce-first-crm-workflow.md`.

**Why now.** The usage-data layer is being absorbed into platforms: Stripe closed
Metronome in January 2026, Adyen closed Orb and Salesforce closed m3ter, both on 1 July
2026. Metering and billing are moving into the CRM and the payment rail. The *decision*
layer on top of that data, which discount was approved, on what evidence, and did it
work, is still nobody's product. That is the window, and it is measured in months rather
than years. See `vault/Competitive/2026-08-09-metering-landgrab-why-now.md`.

If HubSpot is a hard requirement for the live workflow, say so and I will log it. Roadmap
order gets decided by design partners, not by guesses.

## Related

[[readout-close-script]] · [[outreach-sequence]] · [[personas]] · [[data-request]] ·
[[security-one-pager]] · NDA at `docs/legal/one-page-mutual-nda-data-addendum.md`

---

## Added 2026-11-10: AI-pricing motion objections (11 to 18, draft)

These eight belong to the audit-first motion for seed-to-Series-A AI companies, see
[[ai-founder-outreach-sequence]], [[ai-founder-interview-module]] and
`vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md`. They sit outside the
ICP statement at the top of this file (the $10M to $100M, Salesforce-first, 500-closed-deals
screen), which is unchanged and does not apply to this motion. House rules still apply:
concede what is true, say our caveats first, never overclaim. Pricekeel has no customers and
has run no audit yet; the audit is new and the offer one-pager and price are still pending
review, so no price is quoted in any answer below.

| # | Objection | Core of the answer |
|---|---|---|
| 11 | "Model prices keep falling, so margin fixes itself" | Unit costs may fall, but mix and heavy-user behavior can move faster; measure per customer before assuming |
| 12 | "Stripe or our billing tool already shows usage and revenue" | Billing shows revenue; provider bills show cost; the gap is the join per customer |
| 13 | "We cannot share provider bills or cost data" | Nothing is needed on the call; later, a per-customer cost export with IDs not names, labelled as declared |
| 14 | "We are too early to worry about margin" | Possibly true; early is when packaging is cheapest to change, but the answer can be "not yet" |
| 15 | "Why pay a stranger with no customers for a pricing audit?" | Correct, so the offer is small, written, and priced to be easy to walk away from |
| 16 | "Buyers want predictability, we are staying flat or per seat" | Possibly right; the audit can conclude that; the question is where flat is subsidising heavy users |
| 17 | "Provider pricing changes every quarter, an audit goes stale" | A snapshot does go stale; the method is the asset, and the audit states its as-of date |
| 18 | "Can you guarantee a margin improvement?" | No; findings are correlational with caveats printed; no guarantee and no performance fee quoted |

### 11. "Model prices keep falling, so margin fixes itself"

Concede it: unit costs for many models have trended down, and betting on that is not
irrational. Two things can still hurt. Usage per customer can grow faster than unit cost
falls, especially with agent loops, and a flat price set before that growth stays flat. And
which customers are expensive is a distribution question, not an average. I am not claiming
yours is a problem. The cheap test is whether you can say, for your top ten customers by
usage, what each cost last month and what each paid. If you can, you are ahead of most. If
you cannot, that is the thing worth measuring before leaning on the trend.

Supporting asset: interview questions 7 to 12 in [[ai-founder-interview-module]] (cost
visibility and heavy-user stories).

### 12. "Stripe or our billing tool already shows usage and revenue"

It does, and it is the right source for the revenue side. What it does not hold is what each
customer cost you at the model provider, GPU or storage vendor. Those bills arrive per
account, per project or per key, not per customer. So the question is who joins them, how
often, and on what key. If the answer is "a script that runs every month and everyone
trusts it", you have solved it and I would like to learn from that. If it is a spreadsheet
someone dreads on Fridays, that join is the work.

Do not name a competitor first. Let them name their tool, then ask what it misses.

Supporting asset: interview questions 13 to 16.

### 13. "We cannot share provider bills or cost data"

Understood, and nothing is needed on a research call. For an audit, the path is smaller than
it sounds: a per-customer cost export keyed on customer ID, no names, no prompts, no
content. Under ADR-006 a founder-supplied export is labelled `declared_cost`, and we never
call it verified margin. A connector-verified basis (`erp_verified`) is a later, separate
step. If cost cannot be shared even as a percentage by customer tier, I would rather say so
early: the audit then stops at billing-side findings and says what it could not see.

Supporting asset: the cost-basis definitions in ADR-006 and the data answer in
interview question 25.

### 14. "We are too early to worry about margin"

Sometimes true, and I would rather hear that than push. Two reasons it still comes up. First,
packaging is cheapest to change before many customers are on a plan, and grandfathering is
real cost once you have them. Second, the first few large customers set a price anchor that
is hard to move. If you have under a handful of paying customers and no variable-cost
concern, "come back later" is a fair answer and I will note it, not chase it.

Supporting asset: scorecard "0 to 6" row in [[ai-founder-interview-module]]: logged as not a
fit now, which is a useful result.

### 15. "Why pay a stranger with no customers for a pricing audit?"

You should not take my word for it. The honest version is: I have not run one yet, you would
be one of the first, and the offer is built around that. It is short and written, so you can
judge the work on one page before committing anything beyond it. You decide at each step
whether to continue, and I would say plainly if the data you have cannot support a finding.
What I bring is a pricing and discount-governance method built on named sources, not a
track record of AI-company engagements. If that is not enough, it is not enough.

Supporting asset: the one-page offer, which is pending founder approval and must not be sent
before it exists. Related to talk track 5 above.

### 16. "Buyers want predictability, we are staying flat or per seat"

You may be right, and the audit can conclude exactly that. Enterprise finance teams do ask
for predictable spend, and some buyers prefer a fixed fee. The question is narrower: under
your flat or seat price, which customers cost you the most, and is that gap small enough to
absorb? If it is, keep the flat price and add a fair-use line or a cap for the tail. If it
is not, the options are a commit with overage, tiers, or a hard cap. Predictability and
usage cost are compatible when the price is a committed band rather than a raw meter.

Supporting asset: interview questions 17 to 19 (buyer pushback).

### 17. "Provider pricing changes every quarter, an audit goes stale"

A snapshot does go stale, and I will not pretend otherwise. Two things reduce the problem.
Every finding carries its as-of date and the provider rates used, so a reader can re-run it.
And what lasts is the method: how cost is attributed per customer, which segments are
exposed, and which thresholds to watch. If a provider reprices next quarter, the sensible
step is to re-run the same method on the new rates. Whether that is worth a recurring
arrangement is a question for after the first audit, not something I am selling now.

Supporting asset: the as-of date convention in every readout, as in the existing readout
structure.

### 18. "Can you guarantee a margin improvement?"

No, and I would be wary of anyone who did. The analysis is retrospective and correlational:
it shows where cost and revenue diverged and what would have happened under alternative
rules, with the caveats printed on the page. It cannot promise what customers do after a
price change. I am also not offering a performance fee or a share of any lift: that
structure is still under internal review and I will not quote it before it is settled.
What I can promise is that every number traces to the rows behind it and that I will say
what the data could not support.

Supporting asset: methodology and caveats sections of the sample readout at
pricekeel.com/sample (for the discount-leakage readout; an AI-margin readout does not exist
yet).
