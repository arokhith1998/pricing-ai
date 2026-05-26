---
title: Cold outreach sequence — leakage diagnostic
created: 2026-05-26
updated: 2026-05-26
tags: [gtm, outreach, sales, cold-email, design-partner]
status: active
---

# Cold outreach sequence — leakage diagnostic

A 3-touch sequence to the champion (Head of Pricing / VP RevOps; see
[[design-partner-targets]]) plus a referral-ask. The single offer is a **free, fast
retrospective discount-leakage diagnostic** run under NDA on a CSV of their last ~4 quarters
of closed deals. One CTA per message: send the CSV under NDA. The data ask itself is in
[[data-request]]; the NDA is at `docs/legal/one-page-mutual-nda-data-addendum.md`.

We have **zero customers**, so there is no social proof and none is invented. The leverage is
(a) founder domain credibility, and (b) the asymmetry of the offer — they spend ~30 minutes
on an export and get a quantified leakage number; we do the work for free.

## Personalization variables

| Variable | Meaning |
|---|---|
| `{{first_name}}` | Champion's first name. |
| `{{company}}` | Prospect company name. |
| `{{title}}` | Their title (Head of Pricing, VP RevOps, etc.). |
| `{{value_metric_guess}}` | Best guess at their metric (API calls, GB, events, credits, seats+usage). |
| `{{pricing_signal}}` | The public signal that flagged them (e.g. "your pricing page lists a platform fee plus per-API-call metering"). |
| `{{referral_source}}` | Mutual connection or community, for the referral template. |
| `{{founder_name}}` | Sender / founder name. |
| `{{calendar_link}}` | Booking link (optional; CSV-first is fine without a call). |

**Why-now angle (one line, reuse across touches):** "End of quarter is when discount leakage
spikes and is also when the data to measure it is freshest — a good moment to baseline it."

## Email 1 — first touch

**Subject options (pick one):**
- `{{company}}'s discount leakage — free read?`
- `Quick question on {{company}}'s {{value_metric_guess}} pricing`

**Body (~95 words):**

> Hi {{first_name}},
>
> I build pricing-intelligence tooling for usage-based SaaS, and I noticed {{pricing_signal}}.
>
> I'm offering a free, retrospective diagnostic to a few Series B/C teams: send me a CSV of
> your last ~4 quarters of closed deals (won and lost) and I'll show you your discount
> leakage %, price realization, and win rate by discount band. Under a mutual NDA, no strings.
>
> It takes you ~30 minutes to export. I do the analysis. End of quarter is the freshest moment
> to baseline this.
>
> Worth a CSV?
>
> {{founder_name}}

## Email 2 — follow-up (send 3–4 business days later)

**Subject:** `Re: {{company}}'s discount leakage — free read?` (threaded reply)

**Body (~80 words):**

> {{first_name}} — following up once.
>
> To be concrete about the output: one page showing your leakage % (booked vs. list ACV),
> realization trend, and which discount bands actually win deals vs. just give margin away.
> Built only from your closed-deal export, under the NDA I'll send first.
>
> If pricing isn't yours to own, point me to whoever runs discount policy and I'll stop
> emailing you.
>
> Want the column list?
>
> {{founder_name}}

## LinkedIn DM variant (use instead of, or alongside, Email 1)

**~55 words — connection-request note or first message:**

> Hi {{first_name}} — I build pricing tooling for usage-based SaaS. Offering a free
> retrospective on discount leakage to a few Series B/C teams: a CSV of your last ~4 quarters
> of closed deals, under NDA, and I send back your leakage % and win rate by discount band.
> ~30 min on your side. Open to it?

## Referral-ask template (warm, via community or mutual contact)

**Subject:** `Intro to whoever owns discount policy at a usage-based SaaS?`

**Body (~85 words):**

> Hi {{first_name}},
>
> Quick ask via {{referral_source}}. I'm running free discount-leakage diagnostics for a few
> Series B/C usage-based SaaS teams — they send a CSV of closed deals under NDA, I send back
> their leakage % and win rate by discount band.
>
> Do you know a Head of Pricing or VP RevOps at a company on hybrid/usage pricing who'd want a
> free read on their discounting? Happy to send the one-pager you can forward.
>
> Thanks,
> {{founder_name}}

## Sequencing notes
- Touches: Email 1 (day 0) → Email 2 (day 3–4) → LinkedIn DM (day 6–7). Stop after three.
- Keep the NDA ready to attach the moment they say yes; do not make them ask twice.
- The CSV ask lives in [[data-request]] — send it only after a yes, so the first reply stays low-friction.
- No fake logos, metrics, or customer names. The offer's asymmetry is the pitch.

## Related
[[design-partner-targets]] · [[data-request]] · [[ideal-first-design-partner]] ·
NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`
