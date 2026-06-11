---
title: 'Objection inventory: talk tracks for the eight objections we will actually hear'
created: 2026-06-11
updated: 2026-06-11
tags: [gtm, sales, objections, talk-tracks]
status: active
---

# Objection inventory

The eight objections a VP RevOps, Head of Pricing, CFO, or IT reviewer will actually raise,
with honest answers. House rules: never overclaim, never fake social proof, concede what is
true before answering, and say our own caveats before they find them. The caveats are the
product.

## Summary table

| # | Objection | Core of the answer | Supporting asset |
|---|---|---|---|
| 1 | "We can do this in Excel" | You can pivot the wons; the win-rate-by-band analysis needs lost deals and a calibrated reference, and the diagnostic is free, so Excel verifying it costs you 30 minutes | Sample readout at pricekeel.com/sample |
| 2 | "Our data is too sensitive" | Zero-trust path exists: /upload runs in memory, nothing stored, founder never sees it; or mutual NDA with 30-day deletion certification | pricekeel.com/upload · NDA template · security one-pager |
| 3 | "ChatGPT can do this" | The numbers come from a deterministic, auditable engine; the LLM is confined to narration and never computes a figure | Methodology section of the sample readout |
| 4 | "Why not Pricefx / Vendavo" | Different problem and different decade of company; they are enterprise CPQ-adjacent suites for $100M+ orgs, this is a diagnostic plus monitoring cadence for $15-60M ARR usage-based teams | gtm/personas.md anti-persona section |
| 5 | "You have no customers" | True, and the terms price it in: free diagnostic, capped design-partner cohort of 3, no auto-renewal, fee structure that lets you exit | Design-partner terms in the pilot agreement |
| 6 | "You're one person" | True; the engine is deterministic and tested, scope is deliberately narrow, WIP is capped at 2 concurrent diagnostics so every readout gets full attention, and the NDA carries the deletion and breach commitments regardless of headcount | Security one-pager · NDA |
| 7 | "Is this just a one-time scan?" | The diagnostic is one-time and free; the product is the monthly cadence the $15K pilot stands up: live readouts, decision log, policy monitoring | Readout close script (offer section) · pricing page |
| 8 | "Our CRM export is a mess" | Expected and handled: the ingest maps messy headers, drops dupes, excludes open deals, and discloses every step in writing before any conclusion | gtm/data-request.md · LoadReport section of any readout |

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
$15-60M ARR, where the question is discount governance, not configure-price-quote. If the
diagnostic finds nothing, you have spent 30 minutes finding that out instead of a
six-figure evaluation.

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

## Related

[[readout-close-script]] · [[outreach-sequence]] · [[personas]] · [[data-request]] ·
[[security-one-pager]] · NDA at `docs/legal/one-page-mutual-nda-data-addendum.md`
