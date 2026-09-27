---
title: 'Cold outreach sequence: the smaller-yes ladder'
created: 2026-05-26
updated: 2026-09-26
tags: [gtm, outreach, sales, cold-email, design-partner]
status: active
---

# Cold outreach sequence: the smaller-yes ladder

Six touches over roughly four weeks to the champion (VP/Director RevOps, Deal Desk Lead or
Head of Pricing at a **$10-100M ARR** usage-based or hybrid B2B SaaS closing **500+
opportunities a year**, Salesforce-primary; see [[design-partner-targets]] and
[[personas]]). The old 3-touch sequence opened with the maximum-trust ask (NDA + four
quarters of data). This one climbs a ladder of smaller yeses: read a sample, skim a column
list, try the zero-trust path, and only then send data. The NDA + CSV ask happens in the
reply thread, never in a cold touch.

ARR is the screening proxy. The closed-deal count is the gate, and it is the first thing to
confirm once they reply. Source of record for the ICP:
`vault/Competitive/2026-08-01-salesforce-market-need-assessment.md` and
`vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md`.

We still have **zero customers**, so there is no social proof and none is invented. The
leverage is (a) a specific observation about THEIR public pricing, (b) the asymmetry of the
offer: a free pricing-upside diagnostic, (c) artifacts they can inspect without trusting
us: the sample readout and the self-serve /upload path.

**Hard rules**

- One CTA per touch. Two asks in one email is zero asks.
- CFO is never cold-emailed. The CFO arrives via the champion forwarding the readout.
- CRO is contacted only after the champion is in; the diagnostic names their reps.
- Free diagnostic requires closed-lost rows in the CSV. Won-only files get the sample
  readout and a polite explanation, not a diagnostic.
- Never promise the in-CRM workflow to a non-Salesforce account. The CSV diagnostic is
  CRM-agnostic; the live loop is Salesforce-native. Talk track in [[objection-inventory]] #10.
- Stop the moment they reply, in either direction. The sequence is for silence only.
- Update `docs/ops/funnel-tracker.csv` after every touch.
- **No dated or seasonal hooks in this file.** They expire silently and then get sent.
  Anything time-bound belongs in the send plan for a specific batch, never in the template.

## Personalization variables

| Variable | Meaning |
|---|---|
| `{{first_name}}` | Champion's first name. |
| `{{company}}` | Prospect company name. |
| `{{title}}` | Their title (VP RevOps, Head of Pricing, etc.). |
| `{{value_metric_guess}}` | Best guess at their metric (API calls, GB, events, credits, seats+usage). |
| `{{pricing_observation}}` | One SPECIFIC observation about their public pricing page, not a generic compliment. e.g. "your Scale tier meters per-event but the platform fee jumps 4x between tiers, which usually pushes discounting pressure onto the metered line." |
| `{{blog_or_calc_link}}` | The Pricekeel blog post or calculator most relevant to their pricing model. |
| `{{referral_source}}` | Mutual connection or community, for the referral template. |

## Why-now angle (one line, reuse across touches, no expiry)

Pick one. Both are evergreen: the first is triggered by the prospect's own calendar
whenever it happens, the second is a market fact with a dated source.

- **Policy-cycle trigger (use when you know their cycle):** "Discount policy gets rewritten
  once a year, alongside comp. A measured baseline before that means the new policy is set
  against what actually happened, not against anecdotes." Fire this when a trigger event in
  [[personas]] is observed, not on a calendar date.
- **Market trigger (dated, re-verify quarterly):** "Metering and billing are being absorbed
  into the platforms: Stripe closed Metronome in January 2026, and Adyen closed Orb and
  Salesforce closed m3ter both on 1 July 2026. The usage data is moving into your CRM and
  your payment rail. What nobody is building is the record of which discount was approved,
  on what evidence, and whether it worked." Source and re-verify date:
  `vault/Competitive/2026-08-09-metering-landgrab-why-now.md`.

## The ladder

| Touch | Day | Channel | The smaller yes (single CTA) |
|---|---|---|---|
| 1 | 0 | Email | Look at a sample readout (no data ask) |
| 2 | 4 | Email (threaded) | Skim the 10-column list: "your admin exports this in 30 minutes" |
| 3 | 8 | LinkedIn DM | Connect / reply (lightest possible touch) |
| 4 | 14 | Email (threaded) | Try the self-serve /upload path, zero trust required |
| 5 | 20 | Email (new thread) | Read the post / calculator with their pricing model plugged in |
| 6 | 27 | Email (threaded) | Breakup: yes, redirect, or goodbye |

## Touch 1: the observation + the sample (day 0)

No data ask. The only CTA is to look at a sample readout.

**Subject options:**
- `{{company}}'s {{value_metric_guess}} pricing, one observation`
- `noticed something on {{company}}'s pricing page`

**Body (~90 words):**

> Hi {{first_name}},
>
> I build pricing diagnostics for usage-based SaaS. Looking at {{company}}'s public pricing:
> {{pricing_observation}}.
>
> I run a free pricing-upside diagnostic for a few teams your size: closed-deal CSV in,
> price realization, win rate by discount band, and the deals worth a second look out, with
> every number traceable to the rows behind it.
>
> No ask yet. Here is a sample readout on synthetic data so you can judge the artifact
> first: pricekeel.com/sample
>
> Worth a look?
>
> Adhithya

**RevOps variant (swap paragraph 2):**

> I run a free pricing-upside diagnostic for a few RevOps teams your size: closed-deal CSV
> in, and out comes which discounts actually bought wins, which deals closed off-policy
> without an approval on record, and what quarter-end is costing you. Deal-desk hours go
> into approvals; this shows whether the policy they enforce is the right one.

**Pricing-hire variant (swap paragraph 2):**

> I run a free pricing-upside diagnostic built on named methodology (Nagle reference
> pricing, Simon-Kucher discount governance): closed-deal CSV in, realization and win rate
> by discount band out, with the correlational caveats printed on the page. It is built to
> survive a skeptical CFO read, which makes it useful air cover for whatever you are
> already trying to change.

## Touch 2: the 10-column list (day 4, threaded reply)

CTA: skim the one-pager. Still not asking them to send anything.

**Subject:** threaded reply to touch 1.

**Body (~85 words):**

> {{first_name}}, one concrete follow-up.
>
> The entire diagnostic runs on 10 columns: opportunity ID, account, won/lost, created and
> close dates, segment, tier, value metric, list ACV, booked ACV. Your Salesforce admin
> exports this in about 30 minutes, from any CRM if you are not on Salesforce, and lost
> deals matter as much as won ones, that is where the price story hides.
>
> One-pager with the exact list and export steps attached. Does your export have the
> closed-lost rows, and roughly how many opportunities close in a year?
>
> Adhithya

Attach or link the column one-pager (source: [[data-request]]). The deal-count question is
deliberate: it is the ICP gate, and asking it here saves a wasted readout later.

## Touch 3: LinkedIn DM (day 8)

Lightest touch in the sequence. CTA: a reply. ~50 words, connection note or first message:

> Hi {{first_name}}, I emailed about a free pricing-upside diagnostic for {{company}}
> ({{pricing_observation_short}}). No data needed to evaluate it: there is a sample readout
> at pricekeel.com/sample and the whole input is a 10-column CSV. If discount governance is
> someone else's desk, happy to be pointed there.

**RevOps flavor:** lead with "off-policy deals with no approval on record" as the
observation. **Pricing-hire flavor:** lead with "Nagle-style reference pricing on your own
book, caveats printed."

## Touch 4: the zero-trust path (day 14, threaded reply)

CTA: try /upload. This is the trust-collapse move: they can get the number without
trusting us at all.

**Body (~90 words):**

> {{first_name}}, last practical option, and it requires zero trust in me.
>
> pricekeel.com/upload runs the same diagnostic in your browser session: the CSV is
> processed in memory, never stored, and I never see the file or the result. Export the 10
> columns, drop the file in, read your own number.
>
> If the number is boring, I stop emailing, and you have spent 30 minutes confirming your
> discounting is clean, which is worth knowing before the next policy review anyway.
>
> If it is not boring, I would love to hear what you found.
>
> Adhithya

## Touch 5: the relevant artifact (day 20, new thread)

CTA: read one thing matched to their pricing model. No diagnostic mention until the last
line. Pick the blog post or calculator that matches their model ({{blog_or_calc_link}}):
per-API-call metering, platform fee + usage hybrid, credits, etc.

**Subject:** `wrote this with {{company}}-shaped pricing in mind`

**Body (~75 words):**

> Hi {{first_name}},
>
> Wrote a piece on [topic: e.g. why hybrid platform-fee-plus-usage models leak discount on
> the metered line, and the three policies that contain it]. Used a pricing structure like
> {{company}}'s as the worked example: {{blog_or_calc_link}}.
>
> No pitch in it, just the mechanics and the math. If it names a problem you are seeing,
> the free diagnostic quantifies it on your own book.
>
> Adhithya

**RevOps flavor:** pick the policy-simulation or approval-governance post.
**Pricing-hire flavor:** pick the methodology post (reference prices, band win rates).

## Touch 6: breakup (day 27, threaded reply)

CTA: a one-word reply. Genuine close, not a guilt trip.

**Body (~70 words):**

> {{first_name}}, closing the loop.
>
> I cap this at a handful of design partners and I am filling the slots, so this is my
> last note. Three ways to answer, all fine:
>
> 1. "Interested": I send the NDA and the column list, readout five business days after
>    your validated export.
> 2. "Wrong person": point me at whoever owns discount policy and I leave you alone.
> 3. Silence: I take the hint and you keep the sample readout.
>
> Either way, thanks for reading.
>
> Adhithya

## After a reply: the ask sequence (not part of the cold sequence)

1. **Qualify before anything else:** closed-opportunity count last year, primary CRM,
   named discount-policy owner. If the count is short, run [[objection-inventory]] #9
   (offer the 2-3 year lookback, then the narrower read, then a polite no) rather than
   proceeding on hope.
2. **Yes / curious:** send the mutual NDA same day ("your paper or mine"), with the column
   one-pager. Do not make them ask twice.
3. **NDA signed:** send [[data-request]]. Require closed-lost rows; won-only files do not
   qualify for the free diagnostic.
4. **CSV received:** validate intake, confirm receipt with the row counts we read, and
   commit the readout date: five business days after validated intake. Log everything in
   `docs/ops/funnel-tracker.csv` and follow `docs/ops/data-handling-sop.md` for the file
   itself.
5. **Readout call:** run [[readout-close-script]]. CFO invited by the champion.

## Referral-ask template (warm, via community or mutual contact)

**Subject:** `Intro to whoever owns discount policy at a usage-based SaaS?`

**Body (~85 words):**

> Hi {{first_name}},
>
> Quick ask via {{referral_source}}. I run free pricing-upside diagnostics for a few
> $10-100M ARR usage-based and hybrid SaaS teams with real deal volume: they send a CSV of
> closed deals under NDA, I send back their price realization and win rate by discount
> band, with receipts.
>
> Do you know a VP RevOps, Deal Desk Lead or Head of Pricing at a company on hybrid or
> usage pricing who would want a free read on their discounting? Happy to send the
> one-pager you can forward.
>
> Thanks,
> Adhithya

## Sequencing notes

- Touches 1-2-4-6 are one email thread; touch 5 starts fresh so it does not read as nag #5.
- Keep the NDA ready the moment anyone says yes.
- No fake logos, metrics, or customer names, ever. The offer's asymmetry is the pitch.
- Send Tuesday-Thursday, prospect's morning. Skip major holiday weeks.
- Build the list to 120-150 contacts against [[personas]] before touch 1 goes out;
  expect cold touch-to-CSV conversion in the 1-2% range, not 5-10%.
- Any market fact quoted in a touch (the M&A closes above) carries a re-verify date. Check
  `vault/Competitive/2026-08-09-metering-landgrab-why-now.md` before a batch goes out.

## Related

[[design-partner-targets]] · [[data-request]] · [[personas]] · [[objection-inventory]] ·
[[readout-close-script]] · [[ideal-first-design-partner]] ·
NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`
