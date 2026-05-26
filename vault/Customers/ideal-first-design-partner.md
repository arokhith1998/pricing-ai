---
type: reference
title: Ideal first design partner
date: 2026-05-26
created: 2026-05-26
updated: 2026-05-26
tags: [gtm, icp, design-partner, sales]
ai-first: true
status: active
---

## For future Claude
This is the Ideal Customer Profile (ICP) for our FIRST design partner. As of 2026-05 we have NO
partner and NO data yet (stated) — sourcing is the critical path. Lead wedge into the conversation:
a FREE retrospective discount-leakage diagnostic built from a CSV export of their closed deals.
Use this note to qualify prospects and to write outreach. See [[2026-05-26-kickoff-decisions]].

# Ideal first design partner

## Firmographics (confidence: high)
- **Stage / size:** Series B / early C, **$15–60M ARR** (lower end of the $10–100M band — faster decisions, less procurement friction).
- **Pricing model:** **hybrid** — platform fee + a clear consumption metric (API calls, events, GB, compute, or seats+usage). Avoid pure-seat (no leakage story) and pure-outcome (too bespoke) for #1.
- **GTM motion:** sales-led or hybrid PLG→sales with a **deal desk that already exists but runs on spreadsheets** — they *feel* the discounting chaos.
- **Tech stack:** Salesforce or HubSpot CRM + Stripe/Zuora billing. A warehouse is a bonus, not required (we ingest CSV first).

## Buying roles (confidence: high)
- **Champion / primary user:** Head of Pricing or VP RevOps — owns discount policy, measured on NRR / price realization.
- **Economic buyer:** CFO.
- **Unlocker:** VP Sales / CRO — grants data access and drives adoption.

## Wedge (confidence: high)
> "Send me a CSV of your last 4 quarters of closed deals; I'll show you your discount leakage % and win rate by discount band — free, under NDA." See the NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`.

## Where to source (confidence: medium)
- LinkedIn title search: `"Head of Pricing" OR "VP RevOps" OR "Director, Revenue Operations" OR "Deal Desk"`, filtered to Series B/C in dev-tools, infra/API, data, or vertical SaaS (these skew usage-based).
- Communities: Pavilion, RevOps Co-op, OpenView / Kyle Poyar's usage-based-pricing network.

## Qualifying questions to ask a prospect
1. What's your value metric, and what % of revenue is usage vs. platform fee?
2. Who can approve a discount above policy, and is that logged anywhere?
3. Can you export closed-won/lost opportunities with discount + list price for the last 4 quarters?

## Related
[[2026-05-26-kickoff-decisions]] · [[pricing-frameworks-index]] · the NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`
