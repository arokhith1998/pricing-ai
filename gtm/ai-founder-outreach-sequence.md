---
title: 'AI founder outreach sequence: interview-first drafts and tracker proposal'
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, outreach, ai-founders, interviews, linkedin, email, audit-first]
status: draft
source: 'gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md; vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md'
---

# AI founder outreach sequence

Scope: the new audit-first motion, seed-to-Series-A AI founders. The six-touch Salesforce-ICP sequence in [[outreach-sequence]] is a different motion and is not changed. Candidates come from [[ai-founder-targets]]; the call itself follows [[ai-founder-interview-module]].

**These are drafts. Nothing here is sent by an agent.** The founder reviews, edits, and presses send on every message. Contact routes are limited to the founder's own LinkedIn and any business address the company itself publishes. No guessing or scraping addresses.

## Rules for this sequence

- **Credibility first, no software pitch.** The first touch asks to learn, not to sell. There is nothing to demo and the copy does not imply there is.
- **One ask per touch:** a 30-minute conversation. The 14-day audit appears only in follow-up 1, only for Tier A candidates (score 70 or more in [[ai-founder-targets]]), and only as a short optional sentence. Never in the connection note.
- **Be true.** Pricekeel has no customers and has run no audit yet. No logos, no fake numbers, no implied results. Where the audit is mentioned, say it is new.
- **Observations must be literal.** Say only what is visible on the public page. Never imply you know their margin or that they are losing money.
- **Give something back.** Offer a no-names summary of what founders say, sent after the interviews. Only offer it if the founder will actually write it.
- **No em dashes.** Commas, colons, periods.
- **Stop on any reply**, either direction. The follow-ups are for silence.
- **No quoting a price for the audit.** The $2,500 a month anchor and the share-of-lift option are pending the strategist and CFO reviews.
- **Respect "no".** One decline closes the thread. Log it.
- **No dated hooks** in templates. Anything time-bound goes in the batch send plan.

## Variables

| Variable | Meaning |
|---|---|
| `{{first_name}}` | Founder's first name, as shown publicly |
| `{{company}}` | Company name |
| `{{post_topic}}` | What their pricing-related post was about, in their words, under 8 words |
| `{{post_link_or_quote}}` | A short, accurate paraphrase of one sentence from the post |
| `{{observation_short}}` | One literal fact from the pricing page, under 40 characters, e.g. "seat tiers plus credit top-ups" |
| `{{observation_long}}` | One or two literal sentences on the pricing page or changelog, with the date seen |
| `{{credibility_line}}` | One true sentence about the founder's pricing background. The founder writes this. If none fits, delete the line, do not invent one |
| `{{founder_name}}` | Adhithya |

## Variant selector

- **Variant P (posted about pricing):** the founder posted, wrote or spoke about pricing, margins, token cost or a pricing change within the last 6 months. Use the post as the reason for reaching out.
- **Variant N (no pricing post):** reach out on the visible pricing page. Do not pretend to know them from content they have not created.
- **Strong-signal flag (Tier A):** adds the optional audit sentence in follow-up 1.

## First touch: three channels

Send **one** first touch per candidate: the LinkedIn connection note first. Move to the LinkedIn message after they accept, or to email on day 4 if the note is ignored and the company publishes a business address. Never send the same ask on two channels at once.

### Touch 1a: LinkedIn connection note (under 300 characters)

**Variant P** (about 200 characters filled):

> Hi {{first_name}}, your post on {{post_topic}} stuck with me. I'm talking with AI founders about how they set pricing and where billing gets painful. Not selling anything. Open to a 30 min chat?

**Variant N** (about 230 characters, up to about 265 if `{{observation_short}}` runs long; recount after filling and trim to stay under 300):

> Hi {{first_name}}, I'm researching how AI teams set pricing and handle usage billing. {{company}}'s pricing page caught my eye ({{observation_short}}). Not selling anything, just learning how it was decided. Open to a 30 min chat?

### Touch 1b: LinkedIn message (after they accept, send the next day, about 100 words)

**Variant P**

> Thanks for connecting, {{first_name}}.
>
> Your post made a point I keep hearing: {{post_link_or_quote}}. I'm doing 30-minute conversations with AI founders about two things: how they decided what to charge, and where connecting usage costs to billing gets painful in practice. {{credibility_line}}
>
> I'm pre-product and not pitching anything. I would ask for round numbers only, never customer names or data. In return I will send you a short no-names summary of what founders told me.
>
> Would a 30-minute call in the next couple of weeks work? I will work around your calendar.
>
> {{founder_name}}

**Variant N**

> Thanks for connecting, {{first_name}}.
>
> I'm doing 30-minute conversations with AI founders about two things: how they decided what to charge, and where connecting usage costs to billing gets painful in practice. {{observation_long}} {{credibility_line}}
>
> I'm pre-product and not pitching anything. I would ask for round numbers only, never customer names or data. In return I will send you a short no-names summary of what founders told me.
>
> Would a 30-minute call in the next couple of weeks work? I will work around your calendar.
>
> {{founder_name}}

### Touch 1c: email (day 4 if the connection note is ignored; about 110 words)

Subject options (pick the plainest):
- `{{company}} pricing: 30 minutes to learn how you decided`
- `Question on how {{company}} set its pricing`
- Variant P only: `Your post on {{post_topic}}`

**Variant P**

> Hi {{first_name}},
>
> I read your post on {{post_topic}}: {{post_link_or_quote}}. That is the kind of decision I am trying to understand better.
>
> I'm talking with AI founders for 30 minutes each about how they chose their pricing and packaging, and where reconciling usage cost with billing gets painful. {{credibility_line}}
>
> I'm pre-product and this is research, not a pitch. Round numbers only, no customer names or data. I will share a short no-names summary of what I hear.
>
> Is there a 30-minute window in the next two weeks?
>
> {{founder_name}}

**Variant N**

> Hi {{first_name}},
>
> {{observation_long}} That is what made me want to ask how it was decided.
>
> I'm talking with AI founders for 30 minutes each about how they chose their pricing and packaging, and where reconciling usage cost with billing gets painful. {{credibility_line}}
>
> I'm pre-product and this is research, not a pitch. Round numbers only, no customer names or data. I will share a short no-names summary of what I hear.
>
> Is there a 30-minute window in the next two weeks?
>
> {{founder_name}}

## Follow-up 1 (day 5 after the last touch, same channel and thread; about 70 words)

Adds one small piece of value or a sharper question, not a reminder.

**Variant P**

> {{first_name}}, one specific thing I would love your view on: in your post you said {{post_link_or_quote}}. What did you actually do the last time that came up? Happy to keep it to 20 minutes if that is easier.

**Variant N**

> {{first_name}}, one specific question I am asking every founder: when you last changed how {{company}} charges, what triggered it? Even a two-line reply helps, or 20 minutes on a call if easier.

**Strong-signal addition (Tier A only, append as a final short paragraph, never as the ask):**

> Separately, and only if useful after we talk: I am starting to offer a short written pricing and margin review for a small number of AI teams. It is new and I have not run one yet, so there is no pressure and nothing to decide now.

If the founder has not posted about pricing or margin, do not use the strong-signal addition. Do not use it if the score is under 70.

## Follow-up 2 (day 12 after the last touch, same thread; about 55 words)

Breakup, one-word reply invited.

> {{first_name}}, I will leave this here so I do not clutter your inbox. If a conversation on pricing and billing is ever useful, I would be glad to hear from you. If someone else on your team owns it, a pointer is just as welcome. Either way, thanks for reading.
>
> {{founder_name}}

If they answer "wrong person" or point to someone else, treat that as a reply, stop, and log the referral as a role only.

## Replies: what happens next

1. **Yes:** offer two slots, send a calendar invite, and send the opening framing from the interview module in the invite so the "no pitch, no data" frame is set in writing.
2. **Not now:** thank them, ask permission to check back, log a next date. Do not argue.
3. **Asks "what are you selling?":** answer honestly: "Nothing yet. I'm pre-product and working out whether pricing and cost reconciliation is a real problem for AI teams. A short audit service is one thing I might offer, and it comes after the research, not instead of it."
4. **Asks for price or a demo before the call:** do not quote. "Fair question. Let me understand your situation first and then we will both know if it is worth discussing."

## What to log in docs/ops/funnel-tracker.csv per touch (proposal only, the file is not edited here)

The existing tracker is built for the Salesforce-ICP motion: it has NDA, CSV, intake and readout columns that do not apply to an interview. Putting this motion in the same file would also pollute stage counts. **Recommendation:** keep a separate file, `docs/ops/ai-founder-interview-log.csv`, with the columns below, and keep the main tracker for the NDA/CSV/readout motion. If the founder prefers one file, add the first two columns and make every count filter on them.

**Separation rules (the standing rule on fixtures):**
- `record_type` is `real` or `synthetic`. Synthetic rows live only in an `*-example.csv`, carry an `EXAMPLE-` company prefix, and are never counted.
- Interviews with no stated price range, no data answer and no payment are counted as positive interviews, never as pipeline.
- No future-dated rows. A row exists only after the touch or call happened.

| Proposed column | Values or format | Why |
|---|---|---|
| `record_type` | `real` or `synthetic` | Keeps fixtures out of traction counts |
| `motion` | `ai-founder-interview` | Separates from the Salesforce-ICP motion |
| `target_company` | company name | Public |
| `contact_role` | public founder title only | No private details |
| `stage_public` | e.g. `seed`, `series-a`, `unverified`, with source and date | Evidence for the ICP filter |
| `rubric_score` and `tier` | number, A/B/C | From [[ai-founder-targets]] |
| `evidence_url` and `evidence_seen_date` | URL, ISO date | Every signal needs a date |
| `touch_n` | 1a, 1b, 1c, FU1, FU2 | Which touch |
| `touch_date` | ISO date, actual send date | Real dates only |
| `channel` | `linkedin-note`, `linkedin-msg`, `email` | Compare channels |
| `variant` | `P` or `N`, plus `strong` flag | Test the post-based variant |
| `copy_version` | short id, e.g. `2026-11-v1` | Know which draft was sent |
| `reply_status` and `reply_date` | none / yes / not-now / no / referral | Response rate by variant |
| `interview_booked_date` and `interview_date` | ISO | Pipeline of calls |
| `provider_dependence` | single / multiple / own-hosted / unknown | Segmentation |
| `pricing_model_today` and `transition_status` | free text / none, planned, in-progress, done | Core ICP variable |
| `cost_visibility` | measured / estimated / unknown | Interview module section C |
| `heavy_user_story` | none / yes, magnitude range | Section D |
| `reconciliation_method` and `hours_per_month` | free text, number | Manual workaround test |
| `clarity_line` and `clarity_reaction` | A or B; code from the module | 10-word clarity test |
| `scorecard_total` | 0 to 16 | Interview module scorecard |
| `audit_offered` and `audit_response` | y/n, free text | Close outcome |
| `audit_price_range_stated` | their numbers, as ranges | Willingness to pay |
| `data_sharing_answer` | none / cost export as percent / billing export stripped / never | Access test |
| `co_decider_role` | role only | Buyer alignment |
| `intro_source` | role only | Warm paths |
| `notes` | plain text, including leading-question slips and "positive interview only" where it applies | Honest record |

Per touch, the minimum to log the same day is: record_type, target_company, touch_n, touch_date, channel, variant, copy_version, evidence_url and its seen date. Everything else is logged after replies or calls.

## Related

[[ai-founder-targets]] · [[ai-founder-interview-module]] · [[outreach-sequence]] · [[objection-inventory]] · [[personas]]
