# Design: "AI pricing and margin audit" calculator (lead magnet)

**Date:** 2026-11-10 · **Status:** proposed, not on the board · **Author:** web-engineer (design only, no code written)
**Sources read:** `gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md` (Opportunity move 5, the 30-day checklist, Consumer Trends bottlenecks 1, 2, 3), `vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md`, `web/src/app/calculator/page.tsx`, `web/src/components/LeakageCalculator.tsx`, `web/src/app/api/lead/route.ts`, `web/src/lib/store.ts`, `web/src/lib/notify.ts`, `neon/schema.sql`, `web/src/app/privacy/page.tsx`, `docs/design/2026-11-09-site-redesign.md`, `docs/agents/DECISIONS.md` ADR-006, `docs/agents/OWNERSHIP.md`, `python tools/agentctl.py status` (snapshot 2026-11-10T22:51Z, 0 of 4 active), and the `web/src/components/ui/*` primitives on `origin/main`.

The founder's sheet is the founder's synthesis, not evidence. Nothing in it may reach the page as a fact about the market.

## 0. What exists today, and what this reuses

- `/calculator` is the discount-leakage estimator: booked ACV and average discount in, pure client-side math out, no network. It is about discounting, not cost. The backlog task that restyles it (the PK-79 line) claims `calculator/page.tsx`, `LeakageCalculator.tsx` and `test/calculator-page.test.ts`. This design does not touch them. The new tool is a separate route, `/margin-audit`, so there is no claim collision and the leakage calculator keeps its "no signup, no data leaves your browser" promise.
- `POST /api/lead` takes name, company, email, job title, function, revenue range, pricing model and consent, rate-limits (5 per minute), drops honeypot hits, rejects personal email domains (`isCompanyEmail`), calls `saveLead` (a Neon `leads` row plus `notifyLeadCaptured`), then sets the `pk_lead` cookie, which unlocks the gated sample. It has no `source` field and the `leads` table has no `source` column.
- `web/src/components/ui/*` (Section, PageHeader, Card, Stat, StatusPill, SyntheticTag, Button, DataTable, FooterDisclosure) is on `origin/main` but not on `feat/agent-engineering-org`. The build must branch from `origin/main`. `SyntheticTag` has two variants today (`sample`, `illustrative`). `FooterDisclosure` renders `GLOBAL_DISCLOSURE` from `site-nav.ts`, which says every figure on the site is a synthetic sample, and hides itself only on app routes.

## 1. Purpose and the visitor's job

**Visitor's job.** "I run pricing, finance or product at a company that sells an AI feature or product. I suspect some customers cost more to serve than they pay. In two minutes, with my own rough numbers and without handing over data, I want to know whether that is true, at what usage it starts, how much revenue sits with those customers, and what shape of pricing would stop it." The calculator answers those from nine or fewer typed numbers. It does not know the visitor's real per-customer cost. That needs a billing export joined to a cost export, which is what the 14-day audit does by hand and what the product later does from `declared_cost` or `erp_verified` data (ADR-006).

**The ten-word line it supports.** The sheet's example, "We stop AI companies from losing money on heavy users", is exactly ten words, and its test is "under 10". Proposed, nine words: **"Find the customers your AI pricing loses money on."** It promises a diagnosis, not autonomous pricing, and it matches the output: a named band plus the usage level at which a customer turns unprofitable. Fallback in the sheet's own wording: "We show where heavy users cost you money." (eight words). The founder picks; this is a headline candidate only.

**What it is not.** Not a benchmark, a forecast, a price recommendation, or a statement about the visitor's real margin. It is arithmetic on the visitor's inputs, shown in full.

## 2. Inputs

Smallest set that gives a useful result. USD only in v1, stated on the page. Nothing is prefilled except one labelled default.

| # | Field (label on page) | Shown when | Type and valid range | Blank means |
|---|---|---|---|---|
| 1 | "How do you charge today?" | always | `flat`, `per_seat`, `usage`, `hybrid` | not enough to score |
| 2 | "Fee per customer per month" (flat), "Price per seat per month" (per_seat), "Platform fee per customer per month" (hybrid). Symbol `B` | flat, per_seat, hybrid | 0.01 to 1,000,000 | not enough to score |
| 3 | "Average seats per customer" (`B = seat price x seats`) | per_seat | integer 1 to 100,000 | not enough to score |
| 4 | "Price per unit" (hybrid: "Price per unit above the included amount"). Symbol `p` | usage, hybrid | 0.000001 to 100,000 | not enough to score |
| 5 | "Units included in the platform fee, per customer per month". Symbol `I` | hybrid | 0 to 1e12. A typed 0 is a real answer, "none included" | not enough to score |
| 6 | "Your unit" | always | preset "1M tokens" or "Other" plus a 1 to 24 character label, rendered as plain text | the visible selection "1M tokens", not a hidden assumption |
| 7 | "Customers" `N` | always | integer 1 to 100,000 | not enough to score |
| 8 | "Average usage per customer per month, in your unit" `u_avg` | always | greater than 0, up to 1e12 | not enough to score |
| 9 | "Usage of a heavy customer (90th percentile), in your unit" `u90` | always | `u_avg <= u90 <= 10 x u_avg` (below) | not enough to score |
| 10 | "Model-provider cost per unit" `c` | always | greater than 0, up to 100,000. **A typed 0 is rejected** | unit "1M tokens": the labelled default (2.1). Unit "Other": not enough to score |
| 11 | "Storage and other cost per customer per month" `s` | always | 0 to 1,000,000. A typed 0 is accepted and echoed "you entered 0" | not enough to score. Never silently zero |
| 12 | "Monthly churn" `q` | always | 0.1% to 50%. A typed 0 is rejected | not enough to score |

**Why `u90` is bounded.** The tool models the book as two groups: the top decile at exactly `u90`, the other 90% sharing the remainder so the mean equals `u_avg`, namely `u_bulk = (u_avg - 0.1 x u90) / 0.9`. The bottom group cannot exceed `u90` (so `u_avg <= u90`) and cannot be negative (so `u90 <= 10 x u_avg`: the top decile alone cannot exceed the whole mean). Outside that range the inputs are inconsistent and the page says so (sentences E4 and E5 in section 6) rather than guessing.

**Blank rule (hard).** A blank is never coerced to 0 and never carried over from an earlier value. If any field required for the chosen model is blank or invalid, the result area shows "Not enough to score." and lists the fields still needed. It renders no band, no percentage, no dollar figure. The single blank that resolves to a value is field 10 under "1M tokens", and that value is labelled on screen as a default.

### 2.1 The one default: provider cost per 1M tokens

Blended price per 1M tokens, `0.75 x input price + 0.25 x output price`, from the published API price lists of three providers, shown with its sources. The 75/25 split is an assumption, displayed and editable ("Assumes 3 input tokens for every 1 output token").

- OpenAI API pricing: https://openai.com/api/pricing/
- Anthropic API pricing: https://www.anthropic.com/pricing
- Google Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing

**The numeric default is deliberately not written here.** This design was written without a browser, list prices change often, and a stale number on a trust page is worse than none. The build task reads the three pages on the day it builds and records, in `web/src/lib/margin-audit-defaults.ts`, `{ value, split, sources: [{ provider, model, url, retrieved: "YYYY-MM-DD" }] }`, using each provider's mid-tier model (not the flagship) and the median of the three blends. The URLs above are to be reconfirmed at that time. The page shows "Default from public price lists, {retrieved date}. Not your cost. Use your invoice figure." with the three links. A test asserts three sources, valid URLs and an ISO date. A founder reminder re-verifies every 90 days, the cadence already used for the LinkedIn algorithm check. The default is a convenience, not a claim about what the visitor pays: committed-use discounts, other models and self-hosting all differ.

## 3. Formulas

Deterministic TypeScript in a pure module `web/src/lib/margin-audit.ts`. No LLM, no network, no randomness. Constants are named and exported so the page can print the formula it ran.

**Vocabulary (ADR-006).** Every cost figure is typed by the visitor, so the basis is `declared_cost`, whose label is "contribution margin, customer-supplied cost basis". The page never says "gross margin" (the `erp_verified` label) and never says "verified". Below, "margin" means contribution margin on the visitor's declared costs. This departs from the founder's phrase "gross margin" in the sheet; the departure is required by ADR-006.

### 3.1 Revenue, cost, margin per customer

```
Rev(u) = B + p * max(0, u - I)
  flat:     B = fee,                    p = 0,           I = infinity
  per_seat: B = seat price * seats,     p = 0,           I = infinity
  usage:    B = 0,                      p = unit price,  I = 0
  hybrid:   B = platform fee,           p = overage,     I = included units

C(u) = c * u + s
M(u) = Rev(u) - C(u)          margin per customer per month at usage u
margin % = M(u) / Rev(u)      shown only when Rev(u) > 0
```

Reported: `M(u_avg)` and `M(u90)`, each in dollars and percent.

### 3.2 Heavy-user break-even

The usage level at which margin per customer turns negative, found as the first crossing from non-negative to negative as usage rises.

- **flat and per_seat, one line:** `u* = (B - s) / c`. Customers above `u*` units a month are underwater. If `B <= s`: "negative before any usage".
- **hybrid:** inside the allowance, `u1 = (B - s) / c`; if `u1 <= I` then `u* = u1`. Otherwise margin at `I` is positive and the slope above `I` is `p - c`. If `p < c`: `u* = (B - s - p*I) / (c - p)`. If `p >= c` and `u1 > I`: no break-even.
- **usage:** the sign depends on unit economics, not heavy use. If `p > c`: no heavy-user break-even, and the page instead states the floor `s / (p - c)` units a month a customer needs to cover storage and other cost. If `p <= c`: negative at every level of usage.

Also shown, when `u*` exists: `u90 / u*`, as "x times the break-even level".

### 3.3 Portfolio view and revenue at risk

```
R_tot = N * ( 0.9*Rev(u_bulk) + 0.1*Rev(u90) )     monthly revenue
C_tot = N * ( c*u_avg + s )                         monthly cost (exact; cost is linear)
blended margin % = (R_tot - C_tot) / R_tot
top-decile shortfall $/month = 0.1*N * max(0, -M(u90))
revenue at risk share = 0.1*N*Rev(u90) / R_tot   if M(u90) < 0, else 0
```

"Revenue at risk" is the share of revenue from customers whose margin is negative at `u90`. It is a lower bound: the real top decile uses at least `u90` and the model sets it to exactly `u90`. The sentence says "at least".

### 3.4 Packaging signal

One of five signals, first match wins. A direction to examine, never a price.

1. Any required field blank or invalid: `NOT_ENOUGH`.
2. `flat` or `per_seat`, and (`M(u90) < 0` or `u90 >= 0.5 x u*`): `ADD_USAGE_COMPONENT`. The cost-covering fee at p90, `c x u90 + s`, is displayed as a stated fact, with no statement of what to charge.
3. `hybrid`, and (`p < c` or `u* <= I`): `FIX_OVERAGE_OR_ALLOWANCE`.
4. `usage`, and `(p - c) / p < 0.40`: `UNIT_PRICE_NEAR_COST`.
5. Otherwise `STRUCTURE_COVERS_P90`. For `usage` and `hybrid`, when `u90 / u_avg >= 3`, a non-scored note about bill predictability is added.

**Not scored, and the page says so:** seat compression (revenue falling as AI replaces seats), output quality, pilot revenue, incumbent bundling. They are bottlenecks 2 (partly), 4, 5 and 6 in the sheet and need inputs this tool does not collect. The score reflects bottleneck 1 (cost floor and negative-margin trap), the packaging signal for bottleneck 2, and churn.

### 3.5 Margin Health Score: a labelled band, not a number

Evaluated top to bottom, first match wins.

| Band | Rule | Reasoning |
|---|---|---|
| **Negative** | `M(u_avg) < 0` or blended `< 0` | Arithmetic: the average customer loses money. No judgment line |
| **At risk** | blended `< 40%`, or `M(u90) < 0` | A negative top decile is the negative-margin trap in bottleneck 1 even when the average looks fine. 40% is a judgment line |
| **Watch** | blended `< 60%`, or (`u*` exists and `u90 >= 0.5 x u*`) | Margin is thin, or the heavy customer is within a factor of two of the break-even level. 60% is a judgment line |
| **Healthy** | none of the above | Says nothing about market position, only that these inputs clear the lines |

**Churn step.** After the band is set, if expected lifetime `1 / q` is under 12 months (monthly churn above 8.33%, about 65% a year, `1 - (1 - q)^12`), the band drops one step: Healthy to Watch, Watch to At risk; At risk and Negative stay. The page says so. It always shows lifetime margin per average customer, `M(u_avg) / q`, labelled undiscounted with no acquisition cost.

**The thresholds are not benchmarks.** 0 is arithmetic. 40%, 60% and the 12-month line are Pricekeel review lines chosen so each band change can be explained in one sentence. None has a source: the sheet's 80 to 90% classic-SaaS margin figure is the founder's unverified synthesis and is not used. **The pricing strategist and the CFO review these three lines before build.** If they move a line, the sentences that quote it (S9, B5) move with it. The page prints the lines beside the band.

**Colour.** Negative and At risk use Leak Coral (#F0654E) with an icon and the word. Watch and Healthy are neutral with the word. Amber is the governance colour and green the realization colour in `brand/PALETTE.md`; this tool is neither, so it uses neither. Colour never carries the band alone.

### 3.6 Sensitivity to model-price deflation

Recompute blended margin with `c` replaced by `c x (1 - d)`, prices held, for `d` = 25% and 50%: `blended_d = 1 - N*(c*(1-d)*u_avg + s) / R_tot`. One sentence under the band (R7). The full table, with a held-price row and a pass-through row (usage price or hybrid overage cut by the same percent), is gated.

### 3.7 Hand-checked reference cases

Unit is 1M tokens. Figures are test fixtures, not price claims.

| Case | Inputs | Results |
|---|---|---|
| A flat, healthy | B=500, N=100, u_avg=2, u90=6, c=10, s=50, q=2% | M(avg)=500-(20+50)=430 (86%). M(p90)=500-(60+50)=390 (78%). u*=(500-50)/10=45. R_tot=50,000. C_tot=100x70=7,000. Blended 86%. u90/u*=0.133. Revenue at risk 0. Band Healthy. Signal STRUCTURE_COVERS_P90 |
| B flat, top decile underwater | B=500, N=100, u_avg=20, u90=100, c=10, s=50, q=3% | M(avg)=500-250=250 (50%). M(p90)=500-1,050=-550. u*=45, u90/u*=2.22. R_tot=50,000. C_tot=100x250=25,000. Blended 50%. Revenue at risk 5,000/50,000=10%. Top-decile shortfall 10x550=5,500 a month. Cost-covering fee at p90=10x100+50=1,050. Band At risk. Signal ADD_USAGE_COMPONENT. Deflation: c=7.5 gives C_tot 20,000, blended 60%; c=5 gives 15,000, 70% |
| C usage | p=20, c=10, s=50, N=100, u_avg=10, u90=30, q=2% | Rev(avg)=200, C=150, M=50 (25%). Rev(p90)=600, C=350, M=250 (41.7%). No heavy-user break-even; floor s/(p-c)=5 units. R_tot=20,000, C_tot=15,000, blended 25%. Band At risk (blended below 40%). Signal STRUCTURE_COVERS_P90, because (20-10)/20=50% is not below 40%. Band and signal are independent |
| D hybrid | B=300, p=20, I=10, c=10, s=50, N=50, u_avg=12, u90=30, q=2% | Rev(12)=340, C=170, M=170 (50%). Rev(30)=700, C=350, M=350. u1=(300-50)/10=25 > I and p >= c: no break-even. u_bulk=(12-3)/0.9=10, Rev=300. R_tot=50x(270+70)=17,000. C_tot=50x170=8,500. Blended 50%. Band Watch. Signal STRUCTURE_COVERS_P90 |
| E churn step | Case A with q=10% | 1/q=10 months, under 12. Healthy lowered to Watch, B5 shown |

## 4. Output screen and gate

One page, three stacked sections with anchors (`#input`, `#diagnostic`, `#recommendation`), matching the sheet's Input, Diagnostic, Optimized Pricing Recommendation. Results update live as fields become valid. Typing submits nothing.

1. **Input.** The form in section 2, fields for the chosen model only. Mobile: one column, 16px inputs, 44px targets.
2. **Diagnostic (free, no email).** The band as a label with icon and word, its one sentence and the lines; headline `Stat`s (margin per customer at average and at p90, blended margin, heavy-user break-even or its no-break-even sentence, revenue at risk with "at least"); the deflation sentence; and an always-visible formula block, in monospace, the formulas for the chosen model with the visitor's numbers substituted. The formula block is the part a CFO can check and the reason the page earns trust, mirroring "How the math works" on `/calculator`.
3. **Recommendation (free).** The packaging signal as a headline plus its sentence, the cost-covering fee at p90 where relevant as a stated fact, and the not-scored list. It never says "set your price to". The decision stays with the visitor.

**Behind the work email (if the founder chooses the gate):** the per-band breakdown (`DataTable`: rows "Bottom 90% of customers" and "Top 10% of customers"; columns usage, revenue, cost, margin per customer, margin %, monthly totals; plus the top-decile shortfall in dollars); the full deflation table in 10% steps to 50% with held-price and pass-through rows; lifetime margin (R8); and the 14-day audit request.

**Gate copy (exact).**
- Heading: "See the full breakdown"
- Body: "The headline result above is free and stays on this page. Enter your work email to see margin by customer group, the full price-drop table, and to request the 14-day audit of your real billing and cost data."
- Email label: "Work email"
- Required checkbox: "I agree to the Privacy Policy." (links `/privacy`)
- Optional checkbox, unchecked by default: "Also send the numbers I typed to Pricekeel, so the audit starts from them."
- Button: "Show the breakdown"
- Under the button: "We will use your email to reply about the audit. No newsletter is added."
- Personal-domain error, reusing the route's text: "Please use your company email address (not a personal one)."
- Success: "Thanks. The breakdown is below. We will email you about the 14-day audit."

**Audit offer (exact).** "The 14-day audit: send a billing export and a cost export, and we compute margin per customer from your real data, find the customers that cost more than they pay, and write up the packaging options. A person does the work and you make the decision. No price is changed for you." It is an offer of work, not software, consistent with the audit-first decision. It names no price (the $2,500 anchor is under strategist and CFO review) and no outcome.

**Honesty line (exact, under the Diagnostic heading and again inside the gate).** "Computed in your browser from the numbers you typed. No benchmark, no comparison to other companies, no stored data. Nothing is sent to us unless you submit your email."

This is true only if the formulas run in the browser. The module is imported by a client component, no calculate endpoint exists, and a test asserts no `fetch` before the gate form submits.

## 5. Lead capture

> **Naming decision (lead, 2026-11-10, PK-108).** The column and the request field are `lead_magnet`, not `source`: `leads.lead_magnet text not null default ''`, where the empty string means the existing sample gate, and the calculator sends `lead_magnet: "margin_audit"`. The CHECK is a format rule (`^[a-z][a-z0-9_]{0,31}$` or empty), so a later lead magnet needs no migration. Everywhere this section says `source` or `'sample_gate'`, read `lead_magnet` and `''`. PK-108 (PR 95) ships the migration; PK-109 ships the write path and must not deploy before the migration is applied to production Neon.

**Reuse `POST /api/lead` with `source: "margin_audit"`.** Absent `source` keeps today's behavior exactly (`sample_gate`). New branch:

- Required: `email` and `consent`. Name, company, job title, function and revenue range are not asked. Stored values: `name = ""`, `company =` the email domain, `role_title = ""`, `role_function = ""`, `revenue_range = "Unknown"`, `pricing_model =` the model the visitor picked (`flat`, `per_seat`, `usage`, `hybrid`). `isCompanyEmail`, `rateLimit`, the honeypot (still byte-identical, per the comment at `route.ts:25`) and UTM capture apply unchanged. `source` is an allowlist of one value; anything else is treated as absent.
- **Does not set `pk_lead`.** That cookie unlocks the gated sample, and a visitor who typed one email into a calculator has not agreed to the sample gate. The breakdown is revealed by client state only. (If the founder wants the unlock as a bonus, it is one line plus one gate sentence; default is no.)

**Storage.** Add `source text not null default 'sample_gate'` to `leads` (dated Neon migration with a down, `data-engineer` owns `neon/**`; `saveLead` gains the column under a `store.ts#leads` component claim, disjoint from PK-43's `store.ts#access_codes`). **Do not store the typed inputs in the database.** Reasons: they are a business's price, cost and churn figures joined to an identifiable email, which would make `leads` more sensitive than it is now; an email serves the founder's purpose (starting an audit conversation) as well as a row; and it keeps the privacy change to one sentence and the retention story unchanged. A row holds email, domain, `source`, chosen model, consent, UTM. Fallback if a migration is unwanted in v1: set `utm_campaign = "margin_audit"` when none arrived, accepting lost attribution for campaign visitors.

**Resend notification** (`notify.ts`, same best-effort contract, never throws; the webhook payload carries the same fields). Subject: `New margin-audit lead: {email domain} ({band})`, never the full address. Plain-text body:

```
Margin audit calculator lead
Email: {email}
Domain: {domain}
Charges today: {flat|per_seat|usage|hybrid}
Result: band {band}, blended {pct}%, signal {SIGNAL_CODE}
Shared the typed numbers: {yes|no}
{if yes: the twelve inputs, one per line, with units}
Via: {utm_source}/{utm_medium}/{utm_campaign} (if present)
```

Band, percentage and signal are included without the opt-in because the founder needs them to prioritize a reply and they carry no raw cost figures. Inputs are included only when the optional box was ticked. The client sends `shared_inputs` and, only if true, an `inputs` object. The route treats the client as untrusted: it bounds every number with the section 2 ranges, and when inputs are present it recomputes band and signal server-side with the same pure module instead of trusting the client's band. When inputs are absent it accepts only a band label from the allowlist. With the opt-in, Resend and the founder's inbox hold the numbers; that is the privacy consequence, and the privacy sentence says so.

**Privacy page sentence to add** (`web/src/app/privacy/page.tsx`, beside the lead-details paragraph): "If you use the AI pricing and margin audit calculator, the numbers you type are processed in your browser and are not sent to us unless you submit your work email. If you also tick the box to share them, we receive them in an email notification and keep them with that request; we do not store them in our database." The page and `web/test/legal-text-frozen.test.ts` are claimed by the PK-52, PK-62, PK-69 chain and the PK-82 legal-layout task. The sentence is a deliberate wording change that must update that frozen test, so it is a separate later task or a lead-granted exception. **The gate must not ship before the sentence does.**

## 6. Evidence boundary and copy rules

Authority: the honesty rules in `docs/design/2026-11-09-site-redesign.md` (no users, customers, pilots, logos, testimonials, counts or traction; no autonomous price-setting; no "learns from your data" without the cold-start limit; no CRM proxy called margin; billing or ERP required for margin) and `vault/Competitive/2026-08-01-salesforce-market-need-assessment.md`.

**Provenance has a third case.** The PK-75 global rule says every figure is synthetic or illustrative. Here every figure is the visitor's own input or arithmetic on it, plus one default that is a public list price. So:
- `GLOBAL_DISCLOSURE` is false on this route. A route-keyed provenance override in `site-nav.ts` renders: "Every figure on this page is computed from the numbers you typed. Pricekeel supplies no data, and the one default is a public list price, labelled where it appears." Leaving the footer as is would put a false sentence on the page.
- `SyntheticTag` gets a third variant, "Your inputs, not Pricekeel data", on the results header and each figure group. The default price carries its own tag (S10). Neutral tone, never a status color.
- **ADR-006:** basis is `declared_cost`. Every margin figure carries the caption S6, the exact string held in one constant and never re-typed. The page never says "gross margin", "verified", "true margin" or "actual margin". S7 states that the figures are the visitor's own inputs and unchecked. This is the existing billing-or-ERP disclosure, kept intact: margin is the visitor's own claim until a billing or cost system confirms it.

**Copy lives in one module**, `web/src/lib/margin-audit-copy.ts`, as ids and template strings with `{slots}`. The page renders only from it. Review reads this list, and the rendered-copy test proves the DOM holds nothing else. No em dashes, no "proven", no customer claims.

**Static**
- S1 Title: "AI pricing and margin audit"
- S2 Headline: "Find the customers your AI pricing loses money on."
- S3 Subhead: "Type in how you charge, what a typical and a heavy customer use, and what the model costs you. See where margin turns negative, with the math shown."
- S4 Badge: "Free · runs in your browser · no benchmark"
- S5 Honesty line: as in section 4.
- S6 Basis caption: "contribution margin, customer-supplied cost basis"
- S7 Basis note: "The cost figures are yours. Pricekeel has not checked them against a billing or cost system."
- S8 Not scored: "Not scored here: seat compression, output quality, pilot revenue, incumbent bundling. These need information this tool does not ask for."
- S9 Bands: "Bands: Negative below 0%. At risk below 40%. Watch below 60%. These are our review lines, not industry benchmarks."
- S10 Default tag: "Default from public price lists, {date}. Not your cost. Use your invoice figure."
- S11 Default assumption: "Assumes 3 input tokens for every 1 output token."
- S12 "Not enough to score." S13 "Still needed: {fields}." S14 "All amounts in US dollars."

**Errors**
- E1 "{Field}: enter a number from {min} to {max}."
- E2 "Cost per unit must be more than 0."
- E3 "Enter at least 0.1%. Zero churn is not something this tool can score."
- E4 "A 90th percentile below your average means a few very heavy customers pull the average up. This tool cannot model that shape. Enter a 90th percentile at or above your average, or ask for the audit."
- E5 "Your heavy-customer usage is more than ten times your average, which cannot hold: the top 10% alone would exceed the average. Check both numbers."

**Band**
- B1 Negative: "On your numbers the average customer costs more than it pays."
- B2 At risk: "On your numbers the book is thin, or your heaviest customers cost more than they pay."
- B3 Watch: "On your numbers margin is thin, or your heavy customers are within a factor of two of the usage level where they turn negative."
- B4 Healthy: "On your numbers margin clears our review lines. That says nothing about how you compare with other companies."
- B5 Churn step: "Monthly churn of {q}% means a customer lasts about {months} months on average, so thin margin has little time to compound. The band was lowered one step for that."

**Results**
- R1 "An average customer leaves {amount} a month ({pct}%)." Negative form: "An average customer loses {amount} a month ({pct}%)."
- R2 "A customer at the 90th percentile leaves {amount} a month ({pct}%)." Negative form: "A customer at the 90th percentile loses {amount} a month ({pct}%)."
- R3 "Margin turns negative above {u} {unit} a month per customer." R3a "Margin is negative before any usage: the fee does not cover storage and other cost." R3b "No break-even: each extra unit earns more than it costs." R3c "Negative at every level of usage: each unit costs at least what it earns." R3d "Each customer must use at least {u} {unit} a month to cover storage and other cost."
- R4 "Your heavy customer is at {x} times that level."
- R5 "At least {pct}% of revenue comes from customers who cost more than they pay at the 90th percentile." R5a "No revenue sits with customers who cost more than they pay at the 90th percentile."
- R6 "Across your book, margin is {pct}% on these inputs."
- R7 "If your model cost per unit fell by 25%, margin on these inputs would move from {a}% to {b}%. If it fell by 50%, to {c}%. Prices held. This is a what-if on your numbers, not a forecast of what providers will charge."
- R8 (gated) "Undiscounted margin over an average customer's lifetime: {amount}. No acquisition cost included."

**Signals**
- G1 ADD_USAGE_COMPONENT: "A flat or per-seat price leaves your heavy customers uncovered. Look at a usage component or an included-usage limit. A fee of at least {fee} would cover a 90th-percentile customer's cost on these inputs. What to charge is your decision."
- G2 FIX_OVERAGE_OR_ALLOWANCE: "Your hybrid structure leaks. Either the price above the included amount is below your cost per unit, or margin turns negative inside the included amount. Look at both."
- G3 UNIT_PRICE_NEAR_COST: "Your unit price leaves less than 40 cents of each dollar after model cost. Look at the unit price or the cost per unit."
- G4 STRUCTURE_COVERS_P90: "On these inputs your structure covers a 90th-percentile customer's cost."
- G5 predictability note: "A customer at the 90th percentile pays at least three times the average bill. Whether your buyers accept that is a question for them, not for this tool."

**Gate and offer:** the exact copy in section 4 (heading, body, labels, button, success, offer).

**Rules the rendered-copy test enforces**
1. No em dash or en dash used as a dash in rendered text, metadata or the email body.
2. Banned strings, case-insensitive: "proven", "guarantee", "autonomous", "automatically set", "AI-powered", "learns from", "customers like you", "peers", "industry average", "benchmark" (allowed only inside S4, S5 and S9, which negate it), "gross margin", "verified", "true margin", "actual margin", "save you", "recover".
3. Every number rendered is computed from the inputs, one of the named threshold constants, or the labelled default.
4. No sentence states or implies a customer, count, logo, testimonial or result.
5. The audit offer names no price and no outcome.
6. S6 appears wherever a margin figure appears; S7 appears with the first result.

**ICP conflict.** The decision record leaves open whether the target is the site's $20M to $100M ARR usage and hybrid B2B SaaS or seed-to-Series-A AI companies. This page therefore says "if you sell an AI feature or product" and states no ARR band, stage or customer type. It is usable under either ruling.

## 7. Tests (Vitest, in `web/test/`)

1. **`margin-audit-formulas.test.ts`** (pure module).
   - Cases A to E in 3.7 to the cent and to 0.1 percentage points, covering `u*`, `u_bulk`, `R_tot`, `C_tot`, revenue at risk, band, signal, deflation.
   - Never-zero and blank: each required field blank returns `NOT_ENOUGH` with no numeric output populated (not 0, not NaN); typed `c = 0` is an error; typed `q = 0` is an error; blank `s` is not enough while typed `s = 0` scores and echoes "you entered 0"; unit "1M tokens" with blank `c` uses the flagged default; unit "Other" with blank `c` is not enough.
   - Consistency: `u90 < u_avg` returns E4, `u90 > 10 x u_avg` returns E5.
   - Boundaries: blended exactly 0%, 40%, 60%; `u90 = 0.5 x u*` exactly; `1/q = 12` exactly (no step) versus just under (step).
   - Hybrid: break-even inside the allowance, in the overage with `p < c`, none with `p >= c`, and `B <= s`.
   - Property loop on seeded random valid inputs: `C_tot = N x (c x u_avg + s)`; `0.9 x u_bulk + 0.1 x u90 = u_avg`; band never improves as `c` rises.
   - Determinism: same inputs, identical output.
2. **`margin-audit-copy.test.ts`**: render page and component with `renderToStaticMarkup` for one fixture per band, per signal, and the not-enough state. Assert every sentence matches a copy-module entry after slot substitution, the banned list finds nothing, S5, S6 and S7 are present, no em dash, the default tag shows its date and three links, metadata passes the same checks, every input has a label, errors use `aria-describedby`, the result region is `aria-live="polite"`, and band and signal are not conveyed by colour alone.
3. **`margin-audit-lead.test.ts`**, extending the `lead-route.test.ts` pattern with `saveLead` mocked at the module boundary and `vi.stubGlobal("fetch", ...)` with `RESEND_API_KEY` set. Assert: `source: "margin_audit"` with only email and consent returns 200; `pk_lead` is not set; a personal email and a missing consent are rejected; the honeypot returns the identical `{ok:true}` and calls neither `saveLead` nor `fetch`; unknown `source` falls back to the existing required-fields behavior; the Resend body has the domain and band in the subject but not the full address; no input figures when `shared_inputs` is false, all twelve when true; the server recomputes the band instead of trusting the client; out-of-range inputs return 400; a `fetch` that rejects or returns 500 never changes the 200.
4. **No-network test** (jsdom): type a full valid set, assert `fetch` is never called until the gate form is submitted.
5. **`margin-audit-mobile-overflow.test.ts`**, same structural approach as `web/test/diagnostic-mobile-overflow.test.ts`: jsdom, every table inside a horizontal scroll wrapper, no inline pixel width above 360. The gated breakdown table is rendered in the test because it is the widest element. Use PK-88's deterministic helper if it lands first. A manual 375px screenshot of the three sections goes in the PR.
6. **Provenance test**: this route shows the inputs-provenance line and not `GLOBAL_DISCLOSURE`, and the third `SyntheticTag` variant renders its exact text.

## 8. Build plan

Read the route, `force-static`, metadata and route-handler guides in `web/node_modules/next/dist/docs/` first (`web/AGENTS.md`). The page is a `force-static` server component wrapping one client component, like `/calculator`.

**Create** (no existing claim): `web/src/lib/margin-audit.ts`, `web/src/lib/margin-audit-defaults.ts`, `web/src/lib/margin-audit-copy.ts`, `web/src/components/MarginAuditCalculator.tsx`, `web/src/components/MarginAuditGate.tsx`, `web/src/app/margin-audit/page.tsx`, the four test files in section 7, and a dated `neon/` migration pair adding `leads.source` (up and down; data-engineer).

**Edit, with the claim each needs** (checked against `OWNERSHIP.md` and the status snapshot):
- `web/src/app/api/lead/route.ts`, `web/src/lib/notify.ts`: unclaimed on the board today. Claim both whole.
- `web/src/lib/store.ts#leads`: component claim only. PK-43 holds `store.ts#access_codes`; the two are disjoint.
- `web/src/lib/site-nav.ts` (provenance override) and `web/src/components/ui/SyntheticTag.tsx` (third variant): shared redesign surfaces. Claim explicitly and land before PK-84 (the final site audit, which depends on them) starts, or coordinate with the lead.
- `web/src/app/sitemap.ts`: one added entry. Claim it.
- `web/src/app/privacy/page.tsx` and `web/test/legal-text-frozen.test.ts`: held by the PK-52, PK-62, PK-69 and PK-82 chain. Separate later task or lead-granted exception; the gate waits for it.

**Do not touch:** `web/src/app/calculator/page.tsx` and `web/src/components/LeakageCalculator.tsx` (PK-79), `LeadForm.tsx` and `sample/page.tsx` (PK-80), `globals.css` (PK-84), `Nav.tsx` and `layout.tsx` (no nav entry in v1; the link from `/calculator` is added by PK-79's owner or after PK-79 merges).

**Sequencing.** Branch from `origin/main`. Re-run `python tools/agentctl.py status` at claim time: nothing was in flight on these files at the snapshot, but PK-79, PK-80, PK-52 and PK-82 are in BACKLOG and may start.

**Estimate, in half-days**

| Piece | Half-days |
|---|---|
| Formula module, defaults file (read and record the three price pages), formula tests | 1.5 |
| Copy module and rendered-copy test | 1 |
| Calculator UI, three sections, formula block, mobile | 1.5 |
| Gate component, lead-route branch, notify, lead test with stubbed fetch | 1.5 |
| Provenance override, third `SyntheticTag` variant, sitemap, accessibility and overflow tests, PR | 1 |
| Neon migration with down (data-engineer) | 0.5 |
| **Total** | **7** (3.5 days) |

Plus 0.25 for the privacy sentence task, after the connector chain.

**Prerequisites outside the build:** strategist and CFO review of the 40%, 60% and 12-month lines; the founder's pick of headline (section 1) and the gate decision below.

**Risks.** (1) The visitor's cost figures are unaudited and a band can look more authoritative than the inputs deserve, so S7 and the formula block stay above the fold on mobile. (2) The 40/60/12 lines are judgment, not evidence; if the reviews reject them the copy changes, not the structure. (3) The two-group model understates a heavy tail; "at least" and E4 are the mitigations. (4) The default token price goes stale; the dated constant and 90-day re-verify are the mitigation. (5) Conversion is unknown before launch; the sheet's Searchable comparison is not evidence for this page.

## The founder question (answer before build)

**Do you want the full breakdown and the audit request behind a work email, or the whole result free with the email asked for only after it?** Design default: the headline result (band, break-even, packaging signal) is free; the per-group breakdown, the price-drop table and the audit request sit behind one work email. The gate yields qualified emails, which is the sheet's goal, but loses some completions and puts an email wall on a product whose pitch is trust. No gate earns more goodwill and shares but collects fewer emails and shows the audit offer to people who have not yet seen what the tool is worth. The build is identical either way except the gate component and the lead-route branch, which is why this must be answered first.
