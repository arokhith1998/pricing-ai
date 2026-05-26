---
title: Design-partner sourcing playbook
created: 2026-05-26
updated: 2026-05-26
tags: [gtm, sourcing, design-partner, icp, sales]
status: active
---

# Design-partner sourcing playbook

Sourcing the first design partner is the critical path, not engineering (see
[[2026-05-26-kickoff-decisions]]). This is the operating doc for finding, qualifying, and
reaching the champion. The wedge into every conversation is a free retrospective
discount-leakage diagnostic, run under NDA on a CSV of the prospect's last ~4 quarters of
closed deals. Companion docs: [[outreach-sequence]], [[data-request]].

## Who we are looking for (from the ICP)

Pulled directly from [[ideal-first-design-partner]] — do not re-derive.

**Firmographics**
- Stage / size: Series B / early C, **$15–60M ARR** (lower end of the $10–100M band; faster
  decisions, less procurement friction).
- Pricing model: **hybrid** — platform fee + a clear consumption metric (API calls, events,
  GB, compute, or seats+usage). Avoid pure-seat (no leakage story) and pure-outcome (too
  bespoke) for partner #1.
- GTM motion: sales-led or hybrid PLG→sales with a **deal desk that already exists but runs
  on spreadsheets** — they already feel the discounting chaos.
- Tech stack: Salesforce or HubSpot CRM + Stripe/Zuora billing. A warehouse is a bonus, not
  required (we ingest CSV first).

**Buying roles**
- **Champion / primary user:** Head of Pricing or VP RevOps. Owns discount policy, measured
  on NRR / price realization. This is who we cold-reach.
- **Economic buyer:** CFO. Cares about leakage as lost revenue.
- **Unlocker:** VP Sales / CRO. Grants the data access and drives rep adoption.

## Sourcing query pack

Copy-pasteable strings for LinkedIn Sales Navigator and Google. Builds on the seed title
search in [[ideal-first-design-partner]]. Run each, then filter by headcount (~80–400) and
funding stage (Series B/C) where the tool allows.

**Title / champion searches (Sales Navigator keyword or title field)**

1. `"Head of Pricing" OR "VP RevOps" OR "VP, Revenue Operations" OR "Director, Revenue Operations" OR "Deal Desk" OR "Monetization"`

2. `"Pricing Strategy" OR "Pricing & Packaging" OR "Monetization Lead" OR "GTM Strategy & Operations"`

3. `("Revenue Operations" OR "RevOps") AND ("usage-based" OR "consumption" OR "PLG")`

**Google / LinkedIn X-ray for champions at usage-based companies**

4. `site:linkedin.com/in ("Head of Pricing" OR "VP RevOps") ("usage-based pricing" OR "consumption pricing" OR "deal desk")`

5. `site:linkedin.com/in ("Director of Revenue Operations" OR "Deal Desk Manager") (API OR infrastructure OR developer OR data platform)`

**Company-discovery searches (find the accounts, then find the champion inside)**

6. `("usage-based pricing" OR "consumption-based pricing" OR "pay-as-you-go") ("Series B" OR "Series C") ("API" OR "infrastructure" OR "data platform" OR "developer tools") -careers -jobs`

7. `("platform fee" AND ("per API call" OR "per GB" OR "per event" OR "per credit")) site:*.com pricing`  (an X-ray for hybrid pricing pages — the platform-fee + metered combination is the ICP signal)

8. `("Series B" OR "Series C") SaaS ("deal desk" OR "discount policy" OR "price realization") (RevOps OR "revenue operations")`

**Sales Navigator account filter recipe (not a string, a filter stack)**

9. Headcount 51–500 · Industries: Software Development, IT Services, Data Infrastructure ·
   Recent funding event (last 24 months) · keyword `usage-based OR consumption OR API` in
   company description. Then pivot to people: Function = Operations/Finance, Seniority =
   Director+.

10. Saved-search alert on query (1) scoped to your target account list, so new champions
    surface as people change roles.

## Target-account hypotheses

Categories and archetypes that fit (usage-based / hybrid, ~$15–60M ARR, Series B/C). The
named companies below are **publicly-known usage-based-pricing examples / hypotheses to
verify** — they illustrate the *shape* of a fit. Do **not** assert their ARR, funding stage,
or who their Head of Pricing is as known facts; many are larger than the ICP band or private.
Treat each as "go verify stage, size, and pricing model before outreach."

**Archetypes (size-agnostic, the safest targeting unit)**
1. Developer-tools / API platform billing per call, request, or build minute.
2. Infrastructure / compute platform billing per GB, per hour, or per credit.
3. Data / analytics platform billing per query, per row, or per compute unit.
4. Communications / messaging API billing per message or per minute.
5. Observability / monitoring billing per ingested GB or per host.
6. Payments / fintech infra billing per transaction + platform fee.
7. AI / ML inference platform billing per token or per request, with a platform tier.
8. Vertical SaaS (logistics, healthcare, martech) with a metered usage line on top of seats.
9. Search / vector / database-as-a-service billing per query + storage.
10. Workflow / automation platform billing per run or per task.

**Publicly-known usage-based-pricing examples — hypotheses to verify (NOT verified facts)**
11. Twilio-style messaging API (category exemplar; the named co is far above the ARR band —
    use as a pattern, target smaller peers).
12. Algolia-style search-as-a-service (per-query metering).
13. Vercel-style platform fee + usage build/bandwidth.
14. Pinecone-style vector DB (per-pod / per-query).
15. Tinybird- / ClickHouse-Cloud-style real-time data (per compute).
16. Resend- / Loops-style email API (per-email metering).
17. Baseten- / Modal-style inference compute (per-second / per-token).
18. Liveblocks- / Ably-style realtime infra (per-connection / per-message).
19. WorkOS-style developer platform (per-connection + platform fee).
20. A vertical-SaaS metered example such as a logistics or telehealth platform with a
    per-transaction line.

> Discipline: before adding any of 11–20 to a sequence, confirm (a) Series B/C, (b) ~$15–60M
> ARR or smaller peer, (c) hybrid/usage pricing, (d) a deal desk exists. If any is unknown,
> it stays a hypothesis, not a target.

## Qualification checklist

Extends the three qualifying questions in [[ideal-first-design-partner]]. Use as a pre-call
scorecard; the first three are the original ICP questions, the rest are disqualifiers.

- [ ] **Value metric & mix:** What is your value metric, and what % of revenue is usage vs.
  platform fee? (Want a real consumption component, not pure seats.)
- [ ] **Discount governance:** Who can approve a discount above policy, and is that logged
  anywhere? (If nothing is logged, the leakage story lands harder.)
- [ ] **Data accessibility:** Can you export closed-won/lost opportunities with discount +
  list price for the last 4 quarters? (This is the go/no-go — see [[data-request]].)
- [ ] **Stage / size:** Series B / early C, ~$15–60M ARR. (Too small = no deal desk; too big
  = procurement friction kills a free pilot.)
- [ ] **CRM:** Salesforce or HubSpot. (Confirms the export in [[data-request]] is feasible.)
- [ ] **Pain ownership:** Is there a named Head of Pricing / VP RevOps who owns discount
  policy? (No owner = no champion = no project.)
- [ ] **Authority to share data:** Can the champion get a one-page mutual NDA signed without a
  3-month legal cycle? (See `docs/legal/one-page-mutual-nda-data-addendum.md`.)
- [ ] **Disqualifiers:** pure-seat pricing (no leakage narrative), no deal desk, mid-acquisition,
  or a heavy procurement org that will not move on a free pilot.

## Related
[[ideal-first-design-partner]] · [[2026-05-26-kickoff-decisions]] · [[outreach-sequence]] ·
[[data-request]] · NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`
