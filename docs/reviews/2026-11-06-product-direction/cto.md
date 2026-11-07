---
title: Product direction review, CTO lens (architecture and technical risk)
created: 2026-11-06
updated: 2026-11-06
tags: [review, product-direction, architecture, integrations, security]
status: draft
source: docs/reviews/2026-11-06-product-direction/BRIEF.md
---

**One line:** The engine is already source-agnostic and the CSV path already makes Pricekeel "any CRM", so the platform-agnostic direction is mostly a refactor of the Salesforce-coupled perimeter plus one billing enrichment adapter; margin, BOM, tax and the next pillars should be deferred until a paid pilot exists.

## 1. Findings

**What the code implies (verified).**
- The integration contract is the canonical deal schema, `pricing/schema.py`. `pricing/crm.py::analyze_records` takes `list[dict]` of canonical rows and never touches a vendor. The engine is platform-agnostic today.
- Vendor coupling lives in the perimeter: `web/src/lib/salesforce-*.ts` (1,620 lines: OAuth, describe, SOQL, crypto, token store), `CanonicalCrmDeal` carrying `salesforce_url`, and `api/routers/crm.py` hardcoding `source="salesforce_crm"`, events named `salesforce_writeback_*`, and a log filter (line 583) that only returns Salesforce sources. Error strings in `pricing/crm.py` say "Salesforce". This is a rename-and-parameterize job, not a redesign.
- The schema is deal-grain: one closed won/lost opportunity with `list_acv` and `booked_acv`. Commit, overage rate, and ramp fields exist but are captured, not scored (`docs/agents/DECISIONS.md`, vault `Decisions/2026-08-08-crm-honesty-and-ubp-math.md`).
- `pricing/mapping.py` plus `pricing/ingest.py` already map arbitrary headers (HubSpot "record id" is a synonym). `docs/design/richer-ingest.md` explicitly deferred mapping persistence per prospect. That deferral is now the bottleneck for "any platform".
- Tier A sizing (350 to 480 accounts, any CRM) is already larger than Tier B (130 to 190, Salesforce-native). The direction is consistent with the sizing; the Salesforce-native investment was the narrower bet.

**What the direction gets wrong about the data (the real technical risk).**
- Billing and metering platforms (Stripe, Chargebee, Maxio, Metronome, Orb) hold only customers who bought. They have no closed-lost deals and usually no list price. The diagnostic's core output, win rate by discount band, cannot be computed from billing alone. Billing is an enrichment join for won deals (realized vs committed, actual overage, ramp truth), never a primary source.
- CRMs hold the decision population (won and lost) but not usage truth. CPQ tools hold the best list price and line-level discount (the fix for the degenerate-list risk in `pricing/crm.py::_guard_degenerate_list`), but outcome usually lives back in the CRM. No single system prices a usage-based deal. Every useful configuration is CRM or CPQ for population plus billing for truth, joined on account or contract identity. Identity resolution (`ingest.resolve_identity`, name normalization only today) becomes the dominant engineering cost.

**API-first versus file-first (from general platform knowledge, not verified against current vendor docs).**
- API-first, simple auth, read-only scopes available: Stripe (restricted keys), Metronome, Orb, Chargebee, Pipedrive, Attio, Close, PandaDoc.
- API exists but gated, region-split, or thin enough that a file export is better for a pilot: DealHub, Maxio, Zoho (multi-data-center), Freshsales, Proposify, Salesbricks.
- For a pre-revenue company, every source except one billing system should be file-first. A CSV export with a saved per-source mapping onboards in hours. A native connector costs one to two weeks each plus an app review or marketplace listing, then maintenance forever.

**Governance gaps (verified).**
- `docs/ops/data-register.md` does not exist. `docs/ops/incident-response.md` section 2 depends on it as the scoping source. Acceptable at zero customers, a blocker at the first file.
- Incident response containment (section 3) rotates our keys but never revokes customer integration credentials: stored Salesforce refresh tokens in Neon and `SALESFORCE_TOKEN_ENCRYPTION_KEY` are absent. Adding billing API keys makes this worse, since a Stripe key exposes a customer's entire revenue ledger.
- Incident response data categories are "deal rows, contact details, access codes". Cost and usage data are not a category, so they would have no notification or deletion procedure.
- Legal audit (vault `Decisions/2026-05-30-legal-compliance-audit.md`) rates Terms and DPA as CRITICAL. The 2026-09-27 eval shows the DPA link as generic. I treat the DPA as not yet executed (assumed, not verified).

## 2. What would have to change

1. **Adapter boundary.** Rename `CanonicalCrmDeal` to a source-neutral `CanonicalDeal` with `source_system` and `source_url`. Parameterize `source` in `api/routers/crm.py` and the log filter. Keep Salesforce as the reference adapter, frozen.
2. **A second grain, not a wider deal row.** Billing data enters as a `contract_period_actuals` aggregate (account, period, committed, invoiced, usage units, overage billed), pulled already summarized from the billing API. Raw usage events never enter Pricekeel: they are high volume, often carry end-user identifiers (personal data), and would break the "process in memory and delete" rule.
3. **Persisted mapping per tenant and source.** Header strings and the confirmed mapping only, no rows. This is the deferred item from `richer-ingest.md`.
4. **Reference snapshot.** Today `/crm/workflow` recomputes from the full submitted book on every call, so every guidance request needs a fresh full pull. Any surface outside the web app needs a persisted aggregate snapshot (band win rates, segment references, policy, `evidence_version`, method name, n per band) computed at sync. Aggregates only, so the no-row-retention rule holds. Comparables are row-level and must be fetched live or omitted outside the authenticated app.
5. **Surface-agnostic decision request contract.** One endpoint, `POST /decisions/request`:
   - Request: tenant, `snapshot_id`, source `{system, object_id, url}`, deal terms `{list, proposed_net, currency, term_months, segment, value_metric, committed, overage_rate, ramp}`, authenticated requester identity, surface.
   - Response: verdict (`within_guardrail` | `above_guardrail` | `insufficient_data`), recommended discount, method name (`band_guardrail`), evidence (band stats with n, reference basis), caveat, snapshot version, `decision_id`, allowed actions.
   - Actions post back as decision-log events on `decision_id`. Every surface renders the same payload; no surface computes anything.
6. **Surfaces, in order.** Web deal-desk view (exists) first. Slack approval second, because exceptions are approved in Slack at most deal desks and Slack user identity can replace the self-asserted `actor`, which is an open release gate. Email as notification with a link back only. Browser overlay deferred: one DOM integration per CPQ tool, breaks on vendor UI changes, and enterprise IT blocks unreviewed extensions.

## 3. Risks and tradeoffs

- **Scope creep against the pilot.** Fourteen named platforms times four feature directions is a year of work for a team, not a solo founder before a paid pilot. Each connector built before a partner uses it is pure maintenance cost.
- **Billing platforms are the feared entrant** (vault `Competitive/defensibility-rebuttal.md`). Reading their APIs deeply makes Pricekeel a feature they can copy. Neutrality is the moat only if the decision log is the asset, so invest in the log and the contract, not connector count.
- **Margin (BOM, landed cost, tax).** Supplier prices are often under the customer's own supplier NDAs. Tax positions and margin at a public company can be material non-public information. Net margin after tax requires a tax engine, which Pricekeel must never imitate. This is a higher sensitivity class than deal rows, with no register category, no deletion procedure, and no DPA language. It also collides with "CRM numbers are never called margin" unless every cost input is labeled customer-supplied and unaudited.
- **Next pillars.** Price recommendation and elasticity on a 30 to 500 deal book cannot be causally identified. Shipping them violates explainability over accuracy faster than any other choice. Value-based pricing per customer needs value drivers that live in no system of record; it is consulting, not software.
- **AI token-cost deflation (3a).** A real ICP pattern, but it is a scoring question (effective price per unit over time against a falling cost basis) that needs billing actuals first. It comes after usage-native scoring, not before.

**Build versus defer.**

| Direction | Call | Why |
|---|---|---|
| Platform-agnostic intake | Build, thin | File presets, saved mapping, adapter rename. One billing API only when a partner uses it. |
| Guidance wherever the rep works | Build contract and snapshot; Slack after a partner asks; defer overlay | The contract is cheap and makes every surface trivial later. |
| Next pillars | Defer | No defensible method on pilot-size data. |
| Usage-native pricing | Build second | Most aligned with the ICP: score effective discount on commit plus overage from fields already captured, then validate against billing actuals. |
| Margin, BOM, tax (3b) | Defer, Phase 3 gate | Security and legal surface far exceeds current controls. |
| Value-based per customer (3c) | Defer | No data source. |

## 4. Recommended first increment

**Source-neutral intake v0, about 5 days (backend-engineer 3, web-engineer 2).**
1. Adapter rename and `source_system` parameterization across `web/src/lib`, `api/routers/crm.py`, and the decision log (1 day).
2. Per-source mapping presets (synonym packs) for HubSpot, Pipedrive, Attio, and Close deal exports and PandaDoc and DealHub quote exports, with the confirmed mapping persisted per tenant, headers only (2.5 days).
3. Create the data register; amend incident response to revoke customer integration credentials and rotate the token encryption key (0.5 day, founder).
4. Tests: presets against fixture headers, source filter in the log, no row persistence (1 day).

Validation: one prospect on a non-Salesforce CRM sends an export and reaches a readout without hand-mapping. Do not start until such a prospect is named; the claim that most deals are not on Salesforce or HubSpot rests on a handful of conversations. Next increment (about 4 days): reference snapshot plus `POST /decisions/request`.

## 5. Open questions for the founder

1. Which system does your most advanced prospect actually price and approve in? That one system decides the first billing or CPQ adapter, and nothing else gets built natively.
2. Is the guidance consumer the rep at quote time or the approver at exception time? Rep means a quote-tool surface; approver means Slack. The answer changes the second increment.
3. Is margin guidance something a current prospect asked for, or a vision statement? If a prospect asked, cost data needs counsel-reviewed DPA language before receipt, and that becomes the gate ahead of any build.
