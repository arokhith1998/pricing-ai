---
title: Kickoff decisions — pricing intelligence platform
created: 2026-05-26
updated: 2026-05-26
tags: [decision, kickoff, strategy, architecture]
status: active
---

# Kickoff decisions (2026-05-26)

First working session. Decisions captured as a record; status marks what's locked vs pending.

## DECIDED
- **Second brain:** bootstrap a fresh Obsidian vault from empty, using
  `eugeniughelbur/obsidian-second-brain` conventions as the engine. The three cloned repos in
  `knowledge/` are *tools*, not the user's notes — they contained zero personal pricing content.
- **Data path:** CSV / flat-file ingestion for Phases 1–2. **Snowflake + Fivetran deferred to Phase 3.**
  Rationale: standing up a warehouse in week 1 is premium yak-shaving when CSV proves the wedge for ~$0.
- **Stack posture:** open-source + local first; cloud/enterprise spend (Snowflake, Fivetran, WorkOS, Vanta)
  starts only when a phase or a customer contract requires it.
- **Domain validation:** an advisor (Poyar/Campbell/Rivera archetype) is reachable; use them to
  sanity-check leakage methodology before showing a customer a number.

## DECIDED (confirmed 2026-05-26)
- **Wedge:** lead with the *retrospective discount-leakage diagnostic* (historical CSV only). Live
  deal guidance comes after the model earns trust.
- **Design-partner access: NONE today — "need to source one."** This makes **GTM the critical path**,
  not engineering. Biggest risk to the 90-day goal is now "no partner," not "tech doesn't work."
- **Build-against-synthetic-data first:** with no real data, build the diagnostic on a realistic
  synthetic deal dataset. It doubles as the outreach demo and de-risks the schema for fast onboarding.

## STILL PENDING
- **First customer's value metric** (seats / consumption / outcome) — follows once a partner is named.

## RECOMMENDATION — team / budget / timeline (my call, per request)
- **Phases 1–2 (days 1–60):** founder + Claude as build partner. **No hires.** Near-zero burn.
- **Phase 3 (days 61–90):** add a *fractional* data engineer (~10–20 hrs/wk) for the first live
  Salesforce/Stripe integration + Snowflake setup. No full-time eng or ML hire until a signed
  design partner and a paying pilot exist.
- **Treat 90 days as pre-seed wedge-proving.** The money/partner-closing artifact is the leakage
  diagnostic on real data — not infrastructure, not SOC 2.

## 90-day plan (proposed)
1. Days 1–30 "Show them the leak": CSV ingestion + identity resolution + core metrics + one diagnostic dashboard.
2. Days 31–60 "Predict the next deal": win-probability (LightGBM) with SHAP explanations + discount-band guidance.
3. Days 61–90 "Real-time + safe to adopt": one live integration, in-context guidance, light approval/audit, SSO stub.

## Related
[[pricing-frameworks-index]] · [[ideal-first-design-partner]] · [[2026-05-26-integrations-openai-obsidian]] · NDA template at `docs/legal/one-page-mutual-nda-data-addendum.md`
