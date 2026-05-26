---
title: Data request — closed-deal export for the leakage diagnostic
created: 2026-05-26
updated: 2026-05-26
tags: [gtm, data-request, onboarding, design-partner, schema]
status: active
---

# Data request — closed-deal export

This is the exact data ask we send a prospect once they agree to the free retrospective
diagnostic (see [[outreach-sequence]]). Columns mirror the canonical schema in
`pricing/schema.py` verbatim — keep names identical so onboarding is a column-mapping
exercise, not a redesign.

## What we need

**One row per closed opportunity — both won and lost — for the last ~4 quarters.** A single
CSV (or Excel) export from your CRM. Won-only data hides why deals are lost on price, so the
lost rows matter as much as the won ones.

The diagnostic runs on the **required** columns alone. The **optional** columns sharpen it
(rep, approver, competitor, usage/platform split) but the analysis degrades gracefully
without them — send what you have, do not block on the rest.

## Required columns

These are the minimum set to run the diagnostic. Column names match `pricing/schema.py`
exactly.

| Column | Type | Description |
|---|---|---|
| `opportunity_id` | str | Unique opportunity identifier (one row per opportunity). |
| `account_name` | str | Customer account name as it appears in the CRM (may be messy / inconsistent across rows). |
| `outcome` | enum | Deal outcome: `closed_won` or `closed_lost`. |
| `created_date` | date | Date the opportunity was created (used to derive cycle length). |
| `close_date` | date | Date the opportunity closed (won or lost). Drives quarter-end analysis. |
| `segment` | enum | Customer segment: `SMB` \| `MidMarket` \| `Enterprise`. |
| `product_tier` | str | Plan / package the deal was sold on. |
| `value_metric` | enum | Primary value metric: `seats` \| `consumption` \| `hybrid`. |
| `list_acv` | float | Annualized contract value at LIST price (pre-discount). The reference price for realization and leakage. |
| `booked_acv` | float | Annualized contract value actually booked (post-discount). For lost deals, the quoted ACV at the time of loss. |

## Optional columns

Include any you have; each one adds depth (governance signals, win-rate drivers, hybrid revenue split).

| Column | Type | Description |
|---|---|---|
| `account_id` | str | Stable account identifier if available. If absent we resolve identity from `account_name` during ingestion. |
| `region` | str | Sales region. |
| `industry` | str | Customer industry / vertical. |
| `platform_fee_acv` | float | Portion of `booked_acv` that is fixed platform fee (hybrid deals). |
| `usage_acv` | float | Portion of `booked_acv` attributable to usage / consumption. |
| `term_months` | int | Contract term in months. |
| `quantity` | float | Seats or usage units committed (interpretation depends on `value_metric`). |
| `rep_id` | str | Sales rep identifier. |
| `approved_by` | str | Who approved the discount, if above policy (governance signal). Empty if no approval was recorded. |
| `competitor_present` | bool | Whether a competitor was in the deal (discount-pressure signal). |
| `lost_reason` | str | Reason captured on closed_lost deals (`price` \| `product` \| `no_decision` \| `competitor` \| `timing`). |

## Identity and PII

`account_name` can be messy or inconsistent across rows — different spellings, suffixes, or
duplicates are fine. We resolve account identity on our side during ingestion, so you do not
need to clean it first. **No PII beyond standard CRM account- and opportunity-level data is
needed** — no end-user names, no contact emails, no individuals' personal information. Rep and
approver fields, if sent, are internal identifiers (e.g. `REP-07`), not personal data.

## Data handling

Your data is processed under the mutual NDA and data-handling addendum at
`docs/legal/one-page-mutual-nda-data-addendum.md`, which we sign before you send anything. In
short: your data is used **only** to deliver this diagnostic for you; it is **never** used to
train models that benefit other customers without your written consent; it is encrypted in
transit and at rest with access logging; and it is **deleted or returned on request** (and on
termination, within 30 days, with written certification). Aggregated, fully de-identified
benchmarks are off by default and only ever permitted if your individual data is not
derivable.

## Export cheat-sheet

Practical pointers, not exhaustive — your admin can map fields in a few minutes.

- **Salesforce:** Reports → new Opportunity report → filter `Stage = Closed Won OR Closed Lost`
  and `Close Date = last 4 quarters` → add columns for amount/list price, product/tier,
  segment, owner, created/close dates → Export → Details Only → CSV.
- **HubSpot:** Deals → filtered view where `Deal Stage is Closed Won or Closed Lost` and
  `Close Date` in the last 4 quarters → add the listed properties as columns → Export.
- **Mapping is fine:** your column headers will not match ours exactly (e.g. `Amount` →
  `booked_acv`, `List Price` → `list_acv`). Send your natural export plus a one-line note on
  what each amount field means; we handle the mapping. List vs. booked ACV is the one pair we
  most need disambiguated.
- **If list price isn't a field:** send booked ACV plus the discount % (or the standard list
  price for each `product_tier`) and we will reconstruct `list_acv`.

## Related
[[outreach-sequence]] · [[design-partner-targets]] · [[ideal-first-design-partner]] ·
canonical schema at `pricing/schema.py` · NDA at `docs/legal/one-page-mutual-nda-data-addendum.md`
