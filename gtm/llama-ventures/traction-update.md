---
title: Traction update — the only place Pricekeel traction claims live
created: 2026-09-11
updated: 2026-09-11
type: gtm
tags: [gtm, traction, investor, design-partner, evidence-boundary]
status: active
related: ["[[pitch-base]]", "[[2026-08-01-progress-reset]]", "[[2026-08-09-distribution-manufacturing-adjacency]]"]
confidence: high
sources:
  - "Founder statement 2026-09-11, verified against repo state the same day"
ai-first: true
---

## For future Claude

Single source of truth for what Pricekeel can claim as traction. The `llama-pitch`
agent reads only this file for the traction dimension. One file to keep current,
one file to get wrong. If a claim is not written here, it is not made.

Verification method: every line below was checked against the repo on 2026-09-11.
The founder's account of the conversations is taken at face value; the product
consequences were verified in code.

---

# The honest headline

**Two design-partner conversations in progress. Intro calls only. No NDA, no data
received, no commitment, no revenue.**

That is the strongest defensible sentence as of 2026-09-11. Do not soften it, do
not inflate it, do not say "partners" without the word "conversations."

# What is real, and why it is worth more than the stage suggests

The conversations are early, but they have already changed the product roadmap in
two specific, verifiable ways. That is the actual signal: not the meeting count,
but the fact that contact with real buyers produced concrete direction changes.

## 1. CRM-agnostic ingestion (triggered by design-partner interest in HubSpot)

- **VERIFIED, in code:** the CSV column mapper recognizes HubSpot's per-deal key
  (`record id` in `pricing/mapping.py:29`), so a HubSpot deal export ingests
  through the generic CSV path. HubSpot is also carried in the GTM targeting
  material (`gtm/personas.md`, `gtm/design-partner-targets.md`,
  `gtm/data-request.md`) and in the format fixtures.
- **NOT TRUE, do not say it:** there is no HubSpot OAuth connector. Salesforce is
  the only live connector, and it is the only one that passed live-org acceptance.
- **The honest sentence:** "Ingestion is CRM-agnostic by design and a HubSpot
  export already maps cleanly. A native HubSpot connector is scoped, not built.
  Salesforce is the only live connector today."

## 2. Margin recovery (scoped in response to design-partner interest)

- **VERIFIED, in code:** the canonical schema already carries an optional
  `cogs_acv` field annotated "enables the Phase 3 margin layer"
  (`pricing/schema.py:141-146`). The hook exists.
- **NOT TRUE, do not say it:** there is no margin recovery capability. No
  gross-margin analysis, no pocket-margin objective, no cost-plus logic. The
  leakage diagnostic is deliberately price-based and does not require cost data.
- **The standing rule that still binds:** a CRM proxy is never called margin.
  See `vault/Decisions/2026-08-08-crm-honesty-and-ubp-math.md`.
- **The honest sentence:** "Design-partner interest pulled margin recovery
  forward. The schema already carries an optional COGS field that anticipates it.
  The margin layer itself is scoped, not built, and we will not report a CRM proxy
  as margin."

# What is NOT claimable

- No NDA executed. No customer CSV received. No readout delivered. No pilot
  proposed, signed, or paid.
- `docs/ops/funnel-tracker.csv` is header-only. That is the honest count of
  logged, attributable activity, and it should be filled in as these two
  conversations progress.
- The Aug 1 validation program (15 problem interviews, 5 data-readiness reviews,
  2 paid pilots) is in motion, not complete.
- Zero revenue. Zero paying customers. Zero retention data, therefore every NRR,
  LTV/CAC, and payback figure remains a labeled hypothesis.

# The open strategic question (flag, do not bury)

Margin recovery is the capability the 2026-08-09 decision deliberately deferred to
Phase 3, because true COGS and SKU-grain margin is a second engine and it is the
home turf of Vendavo, PROS, and Zilliant. Two intro calls pulling the roadmap
toward it is either a real demand signal worth following or exactly the pre-seed
scope drift that decision warned against. It is not resolved. If an investor asks
about roadmap discipline, say that openly: the signal is noted, the schema hook
exists, and the build gate is still a paying SaaS pilot.

# The ask (confirmed 2026-09-11)

Pre-seed, $500K to $1M. Use of funds and the 12 to 18 month milestones it buys are
drafted in `gtm/llama-ventures/rehearsal-script.md`, section "The ask." The round
buys down demand risk, not feasibility risk.

# Maintenance

Update this file the moment any of the following becomes true: an NDA is signed, a
CSV is received, a readout is delivered, a pilot is proposed, or a conversation
goes dead. Mirror every change into `docs/ops/funnel-tracker.csv`.
