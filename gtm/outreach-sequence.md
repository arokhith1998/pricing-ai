---
title: 'Cold outreach sequence: the smaller-yes ladder'
created: 2026-05-26
updated: 2026-06-11
tags: [gtm, outreach, sales, cold-email, design-partner]
status: active
---

# Cold outreach sequence: the smaller-yes ladder

Six touches over roughly four weeks to the champion (VP/Director RevOps or Head of Pricing
at $15-60M ARR usage-based or hybrid B2B SaaS; see [[design-partner-targets]] and
[[personas]]). The old 3-touch sequence opened with the maximum-trust ask (NDA + four
quarters of data). This one climbs a ladder of smaller yeses: read a sample, skim a column
list, try the zero-trust path, and only then send data. The NDA + CSV ask happens in the
reply thread, never in a cold touch.

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
- Stop the moment they reply, in either direction. The sequence is for silence only.
- Update `docs/ops/funnel-tracker.csv` after every touch.

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

## Why-now angle (one line, reuse across touches)

- **Through Jun 30 only:** "End of quarter is when discount pressure peaks and when the
  data to measure it is freshest: a good moment to baseline it." This hook expires Jul 1.
  Do not use it in July.
- **Jul 1 onward:** "H2 planning and comp season are when discount policy actually gets
  rewritten: a baseline now means the new policy and the new comp plan are set against
  measured leakage, not anecdotes."

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

**Body (~80 words):**

> {{first_name}}, one concrete follow-up.
>
> The entire diagnostic runs on 10 columns: opportunity ID, account, won/lost, created and
> close dates, segment, tier, value metric, list ACV, booked ACV. Your Salesforce or
> HubSpot admin exports this in about 30 minutes, and lost deals matter as much as won
> ones, that is where the price story hides.
>
> One-pager with the exact list and export steps attached. Does your export have the
> closed-lost rows?
>
> Adhithya

Attach or link the column one-pager (source: [[data-request]]).

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
> discounting is clean, which is worth knowing before comp planning anyway.
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

1. **Yes / curious:** send the mutual NDA same day ("your paper or mine"), with the column
   one-pager. Do not make them ask twice.
2. **NDA signed:** send [[data-request]]. Require closed-lost rows; won-only files do not
   qualify for the free diagnostic.
3. **CSV received:** validate intake, confirm receipt with the row counts we read, and
   commit the readout date: five business days after validated intake. Log everything in
   `docs/ops/funnel-tracker.csv` and follow `docs/ops/data-handling-sop.md` for the file
   itself.
4. **Readout call:** run [[readout-close-script]]. CFO invited by the champion.

## Referral-ask template (warm, via community or mutual contact)

**Subject:** `Intro to whoever owns discount policy at a usage-based SaaS?`

**Body (~85 words):**

> Hi {{first_name}},
>
> Quick ask via {{referral_source}}. I run free pricing-upside diagnostics for a few
> $15-60M ARR usage-based SaaS teams: they send a CSV of closed deals under NDA, I send
> back their price realization and win rate by discount band, with receipts.
>
> Do you know a VP RevOps or Head of Pricing at a company on hybrid or usage pricing who
> would want a free read on their discounting? Happy to send the one-pager you can forward.
>
> Thanks,
> Adhithya

## Sequencing notes

- Touches 1-2-4-6 are one email thread; touch 5 starts fresh so it does not read as nag #5.
- Keep the NDA ready the moment anyone says yes.
- No fake logos, metrics, or customer names, ever. The offer's asymmetry is the pitch.
- Send Tuesday-Thursday, prospect's morning. Skip the weeks of Jul 4 and major holidays.
- Build the list to 120-150 contacts against [[personas]] before touch 1 goes out;
  expect cold touch-to-CSV conversion in the 1-2% range, not 5-10%.

## Related

[[design-partner-targets]] · [[data-request]] · [[personas]] · [[objection-inventory]] ·
[[readout-close-script]] · [[ideal-first-design-partner]] ·
NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`
