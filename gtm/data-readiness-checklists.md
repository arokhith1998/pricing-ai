---
title: Per-source data-readiness checklists (quote tool, billing platform, other CRM)
created: 2026-11-07
updated: 2026-11-10
tags: [gtm, data-readiness, pilot, intake, non-salesforce, checklist]
status: draft
source: docs/reviews/2026-11-06-product-direction/customer-success.md section 2 part (1); docs/reviews/2026-11-06-product-direction/BRIEF.md; pricing/schema.py; docs/design/richer-ingest.md; docs/ops/data-handling-sop.md
---

# Per-source data-readiness checklists

Task PK-19. Draft for founder review. Nothing here has been tested against a real partner
export. There are zero verified design partners, so every statement about what a given tool
exports is a hypothesis to confirm on the call, not a fact about any named vendor's product.

## How this file relates to the existing data request

`gtm/data-request.md` is the CRM-shaped request we send after a prospect agrees to a
diagnostic. This file is different. It is a **checklist the prospect reads against their own
export**, used in the data-readiness review before any file moves. It never asks for data. It
asks "does your export have a column like this?" The same four readiness gates apply to every
source: 500 or more closed outcomes, reliable list and booked values, a documented discount
policy, a named policy owner.

## How to run this on a call

1. Ask which of the three source types is where deals are priced and approved. Open the
   matching section. Do not read all three.
2. Ask the prospect to open their own export screen, or a past export, and read their column
   headers aloud or tick them against the list. Headers only. No rows, no screen share of
   deal data.
3. Mark each column present, absent, or "we call it something else." Different names are
   fine: the header mapper (synonyms, fuzzy match, local embeddings, then a headers-only
   cloud fallback) handles naming, and the review step lets the prospect confirm or override.
4. State the closed-lost gate plainly, before the pilot and not at the readout (see each
   section).
5. Ask the shared-deal-ID question for every system they use.
6. Confirm the access method: CSV or XLSX export only for pilot 1.
7. Gates three and four (documented discount policy, named policy owner) are answered by
   people, not by exports. Ask them out loud and write down the owner's name and role.
8. Close by restating the time-to-first-readout caveat in this file, so no one hears a
   promise that is not made.

Handling reminder: when files do arrive, they go through the web upload path first (in
memory, nothing retained), or the founder-run email path into the BitLocker folder described
in `docs/ops/data-handling-sop.md`. The readiness review itself needs no file at all.

## Rules that apply to all three sections

- **Export only.** CSV or XLSX. No API keys, no OAuth tokens, no event streams, no
  read-only integration users for pilot 1. If a prospect offers credentials, decline and
  restate the export path.
- **Closed-lost lives only in the CRM.** Win rate by discount band needs closed-lost
  outcomes. A billing-only or quote-only partner gets discount leakage and price realization,
  not win rate by band. Say so up front.
- **Shared deal ID.** Ask: is there one deal ID that appears in the CRM, the quote tool and
  billing, or does someone reconcile the systems by hand (spreadsheet, naming convention,
  account name matching)? Hand reconciliation is a flag, not a disqualifier, but it adds
  join work and the join can fail quietly.
- **Clock.** Under two weeks to first readout for one quote tool plus one CRM, counted from
  validated intake (SOP section 3, step 1), not from the call. Add three to five days for
  mapping and join work if three systems are involved. Do not promise two weeks for three
  systems.
- **One-to-many exports.** Quote-line exports have one row per line item, and many lines
  roll up to one deal. The mapper has not yet been built to handle this: it maps headers to
  one row per opportunity. This is a flag. We do not promise that line-level exports work in
  pilot 1. A deal-level or quote-level export avoids the problem.
- **Currency.** One currency per file, or the file is blocked with a disclosure (see
  `pricing.ingest.CurrencyBlockedError`).
- **Naming.** Money columns on CRM exports are deal values or contract values. They are
  never called margin anywhere in this product.

---

## Section 1: Quote or CPQ tool (examples: DealHub, PandaDoc, Proposify, Salesbricks)

Why this source matters: approver and timestamps often live here, sometimes in better shape
than in the CRM.

### Column checklist (tick against your export)

"Maps to" is the canonical field in `pricing/schema.py`. "New, not in schema" means the
column is useful but no canonical field exists today.

| Column you may have | Maps to | Note |
|---|---|---|
| Quote ID or number | New, not in schema (`quote_id`) | Join key candidate. `opportunity_id` only if the tool stores the CRM deal ID here. |
| CRM deal or opportunity ID on the quote | `opportunity_id` | The shared-deal-ID column. Most important column in this section. |
| Customer or company name | `account_name` | May be messy. Resolved at ingestion. |
| Customer ID | `account_id` | Optional. |
| Quote status (draft, sent, accepted, declined, expired) | `outcome` (partial) | See the closed-lost gate below. Status is not the same as a CRM closed-lost. |
| Quote created date | `created_date` | Quote creation is not always opportunity creation. Flag if they differ. |
| Accepted, signed or closed date | `close_date` | |
| Plan or package name | `product_tier` | |
| Product or SKU on the line | `sku` | Line level. See the one-to-many flag. |
| Product family or category | `product_family` | Optional. |
| Seats, units or committed quantity | `quantity` | |
| Term or subscription length | `term_months` | |
| List price (total or annualized) | `list_acv` | Needs annualizing if the quote is multi-year. |
| Quoted or net price (total or annualized) | `booked_acv` | For declined quotes, this is the quoted ACV at the time of loss. |
| Discount percent or discount amount | Derived (not a field) | The engine derives discount from list and booked. A column here helps cross-check and reconstruct `list_acv`. |
| Platform fee versus usage split | `platform_fee_acv`, `usage_acv` | Optional, hybrid deals. |
| Committed amount, minimum commit | `committed_acv` | Optional. Captured, not scored in V1. |
| Overage or on-demand rate | `overage_rate` | Optional. Captured, not scored in V1. |
| Year 1 and year 2 scheduled amounts (ramps) | `ramp_year_1_acv`, `ramp_year_2_acv` | Optional. Year 3 is `booked_acv` by convention. |
| Quote owner or sales rep | `rep_id` | Internal identifier, not a person's contact details. |
| Approver name or role | `approved_by` | Governance signal. Blank if no approval was recorded. |
| Approval chain, step order | New, not in schema | Useful for the decision record. |
| Approval requested and approved timestamps | New, not in schema | Time-to-approve. Not scored today. |
| Renewal flag, renewal uplift | `is_renewal`, `renewal_uplift` | Optional. |
| Currency | `currency` | |
| Customer segment or size | `segment` | Often absent in quote tools. Usually comes from the CRM. |
| Value metric (seats, consumption, hybrid) | `value_metric` | Often absent. May need to be stated once per product tier. |
| Region, industry | `region`, `industry` | Optional. |
| Competitor present, lost reason | `competitor_present`, `lost_reason` | Rare in quote tools. Usually CRM only. |

### Readiness gates: what this source can and cannot satisfy

| Gate | Quote tool |
|---|---|
| 500 or more closed outcomes | Can count accepted quotes. Declined or expired quotes are not a substitute for CRM closed-lost. Treat the count as won-only unless the CRM also supplies closed-lost. |
| Reliable list and booked values | Strongest of the three sources, if the tool holds a list price per line and a final quoted price. Check that list is a real price book, not a typed number. |
| Documented discount policy | Cannot be satisfied by an export. Approval rules configured in the tool are evidence of a policy, but the written policy is a document the prospect confirms exists. |
| Named policy owner | Cannot be satisfied by an export. The approver column shows who approves, not who owns the policy. Ask. |

### Section-specific gates and questions

- **Closed-lost gate.** A quote-only partner gets discount leakage and price realization, not
  win rate by band. Closed-lost opportunities live in the CRM. If the partner wants win rate,
  the readiness review must also cover the CRM section below.
- **Shared-deal-ID question.** Does the quote carry the CRM opportunity ID? If not, does
  someone reconcile quotes to deals by hand, and how (account name, date, amount)?
- **One-to-many flag.** Line-item exports roll up to one deal. The mapper does not handle
  this yet. Prefer a quote-level or deal-level export. Do not promise line-level support.
- **Access method.** CSV or XLSX export only. No API keys or OAuth tokens for pilot 1.
- **Time-to-first-readout.** Under two weeks for this tool plus one CRM, from validated
  intake. Add three to five days if billing is also in scope.

---

## Section 2: Billing platform (examples: Stripe, Chargebee, Maxio)

Out of scope for pilot 1: Metronome and Orb event streams, and any row-level usage events.
They are the highest-volume, highest-sensitivity data and break the in-memory-and-delete
posture. If a prospect's pricing truth lives only in an event stream, this pilot is not the
right shape yet.

Why this source matters: it shows booked-versus-billed truth. Its weakness is that it has no
win or loss.

### Column checklist (tick against your export)

| Column you may have | Maps to | Note |
|---|---|---|
| Subscription ID | New, not in schema (`subscription_id`) | Join key candidate. |
| Customer ID | `account_id` | Optional. |
| Customer name | `account_name` | |
| CRM deal ID stored as metadata or a custom field | `opportunity_id` | The shared-deal-ID column. Many billing setups do not have it. |
| Plan or price name | `product_tier` | |
| Product or price ID | `sku` | Optional. |
| Billing interval (monthly, annual) | New, not in schema | Needed to annualize recurring amounts into `list_acv` and `booked_acv`. |
| Unit amount or recurring price | `booked_acv` (after annualizing) | Billed price, not necessarily the quoted price. |
| List price on the plan or price book | `list_acv` (after annualizing) | Often absent when prices are custom per customer. |
| Coupon, discount or promotion name and percent | Derived (not a field) | Helps reconstruct list. Coupons are not always how sales discounts are applied. |
| Quantity or seats | `quantity` | |
| Subscription start date | `close_date` (proxy) | Start is not the signing date. Flag if they differ. |
| Subscription created date | `created_date` (proxy) | Not opportunity creation. Flag. |
| Contract end date or term | `term_months` | May need deriving from start and end. |
| Committed amount, minimum or prepaid balance | `committed_acv` | Optional. Captured, not scored in V1. |
| Invoiced amount, total billed to date | New, not in schema | Booked-versus-billed comparison. Not scored today. |
| Renewal or upgrade flag, prior price | `is_renewal`, `renewal_uplift` | Optional, may need deriving. |
| Currency | `currency` | One per file. |
| Monthly usage rollup per customer | `usage_acv` (after annualizing) | Monthly or quarterly rollups only. Never row-level events. |
| Subscription status (active, canceled) | Not an `outcome` | Canceled is churn, not closed-lost. Do not map it to `outcome`. |
| Segment, region, industry, rep | `segment`, `region`, `industry`, `rep_id` | Rarely present in billing. Usually from the CRM. |

### Readiness gates: what this source can and cannot satisfy

| Gate | Billing platform |
|---|---|
| 500 or more closed outcomes | Cannot satisfy. Billing holds won customers only. Subscriptions are not closed outcomes, and there are no closed-lost rows. |
| Reliable list and booked values | Partly. Booked or billed price is reliable. List price is often missing when pricing is custom, and the quoted price may differ from the billed price. |
| Documented discount policy | Cannot be satisfied by an export. |
| Named policy owner | Cannot be satisfied by an export. Ask. |

### Section-specific gates and questions

- **Closed-lost gate.** A billing-only partner gets discount leakage and price realization,
  not win rate by band. There are no closed-lost rows in billing. Say so before the pilot.
- **Shared-deal-ID question.** Is the CRM deal ID stored on the subscription or customer in
  billing? If not, does someone reconcile billing customers to CRM deals by hand?
- **Access method.** CSV or XLSX export from the billing admin only. No API keys, no OAuth
  tokens, no restricted keys, no webhooks for pilot 1. API and OAuth for Stripe or
  Chargebee are deferred.
- **Time-to-first-readout.** Billing alone is an incomplete picture. Billing plus one CRM is
  two systems, with the same clock as quote plus CRM. Quote plus CRM plus billing is three
  systems: add three to five days.

---

## Section 3: Other CRM (examples: Pipedrive, Zoho, Close, Attio, Freshsales)

Why this source matters: it is the only place closed-lost lives, so it is the only source
that can support win rate by discount band. This is the same shape as the Salesforce export
in `gtm/data-request.md`.

### Column checklist (tick against your export)

| Column you may have | Maps to | Note |
|---|---|---|
| Deal ID | `opportunity_id` | |
| Organization or company name | `account_name` | |
| Organization ID | `account_id` | Optional. |
| Deal status (won, lost, open) | `outcome` | Open deals are excluded. Only won and lost count. |
| Deal created or add time | `created_date` | |
| Won, lost or close time | `close_date` | |
| Deal value or amount | `booked_acv` (after annualizing) | For lost deals, the quoted value at the time of loss. Confirm what the field means: first-year, total contract, or monthly. |
| List price, price book or product price total | `list_acv` | The one most often missing in other CRMs. If absent, a discount percent field or a standard price per tier can reconstruct it. |
| Discount percent or discount amount on the deal | Derived (not a field) | Helps reconstruct `list_acv`. |
| Pipeline, product or plan | `product_tier` | |
| Product line or SKU on the deal | `product_line`, `sku` | Optional. Deal-product lines are one-to-many, see the flag. |
| Deal owner | `rep_id` | Internal identifier. |
| Lost reason | `lost_reason` | Often free text. Mapped to the five-value vocabulary or left as is. |
| Competitor field | `competitor_present` | Optional. |
| Contract term | `term_months` | Optional. |
| Seats or quantity | `quantity` | Optional. |
| Currency | `currency` | One per file. |
| Segment, company size or employee count | `segment` | Size bands may need mapping to SMB, MidMarket, Enterprise. Flag the thresholds. |
| Region or country | `region` | Optional. |
| Industry | `industry` | Optional. |
| Approver, approval status | `approved_by` | Rare outside CPQ. Often a custom field. Blank if none. |
| Value metric (seats, consumption, hybrid) | `value_metric` | Usually absent. Stated once per product tier. |

### Readiness gates: what this source can and cannot satisfy

| Gate | Other CRM |
|---|---|
| 500 or more closed outcomes | Can satisfy, and the only source type that counts both won and lost. Count closed rows over roughly the last four quarters. |
| Reliable list and booked values | Booked value is usually present. List value is the common gap. Check whether the amount is typed by reps or comes from a product price book. |
| Documented discount policy | Cannot be satisfied by an export. |
| Named policy owner | Cannot be satisfied by an export. Ask. |

### Section-specific gates and questions

- **Closed-lost gate.** This source can support win rate by band, but only if lost deals
  carry a value (quoted or expected) and that value is trustworthy. Many CRMs leave the
  amount blank on lost deals. If it is blank, win rate by band is not computable even
  though the lost rows exist. Ask.
- **Shared-deal-ID question.** If a quote tool or billing platform is also in play, does its
  record carry this CRM's deal ID? If not, who reconciles by hand?
- **One-to-many flag.** If the export is one row per deal-product line, it rolls up to one
  deal and the mapper does not handle that yet. Prefer one row per deal. Do not promise
  line-level support.
- **Access method.** CSV or XLSX export from the CRM only. No API keys, no OAuth tokens for
  pilot 1.
- **Time-to-first-readout.** Under two weeks for one quote tool plus this CRM, from
  validated intake. CRM alone is faster. Add three to five days if billing is also in scope.

---

## What we will not ask for

These are outside the scope of pilot 1, and this review should never turn into a request for
any of them.

- Cost data: cost of goods, margin figures, or cost per unit.
- Bill of materials.
- Supplier names or supplier terms.
- Row-level usage events, including Metronome and Orb event streams.
- End-customer identifiers (the identities of your customers' own users or customers).
- API keys, OAuth tokens, restricted keys, or any credential.
- Contact names, contact emails, or any personal data about individuals.

If a prospect volunteers any of these, thank them, decline it, and restate the export path.
Cost inputs are a separate conversation under a separate data class, and are not part of
this pilot.

## Related

`gtm/data-request.md` · `docs/ops/data-handling-sop.md` · `docs/design/richer-ingest.md` ·
`pricing/schema.py` · `docs/reviews/2026-11-06-product-direction/customer-success.md`

---

## Appended 2026-11-10: AI margin audit (separate motion, draft)

Added for the audit-first motion. It is an exception to the "What we will not ask for" list above,
and only by written amendment (see `gtm/ai-margin-audit-data-request.md`, F-audit-data-class).
Everything above is unchanged.

| Source | Column you may have | Used for | Note |
|---|---|---|---|
| AI margin audit | Invoice lines per customer per month (period, invoiced amount tax excluded, discount, credit, metered units); subscriptions (plan, start, end, pilot flag); model-provider usage and cost export grouped by key, project or workspace, or an app-side per-customer monthly rollup; cloud and storage cost lines; customer list with plan and start date; pricing page and packaging history | Per-customer contribution margin on a customer-supplied cost basis (`declared_cost`), heavy-user tail, packaging review, pilot-to-ARR | Customer codes only, monthly rollups only, no keys, no content. Gates differ: 3 or more months of billing, about 10 or more billed customers, cost attributable per customer, discount policy owner. No usable data, no audit. |
