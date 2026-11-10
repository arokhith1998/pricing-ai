# Founder research sheet, tab: Stack

Source: CTO, 2026-11-10, from the code on origin/main, the margin-health, calculator and connector design docs, ADR-006 and ADR-007. Half-day estimates are the design docs' own, uncalibrated.

1. What is live today, by layer

Site: Next.js on Vercel at pricekeel.com. Marketing pages, the leakage calculator and the lead form, which saves to Neon and emails the founder through Resend.

API: FastAPI on Render at api.pricekeel.com, behind a shared secret and rate limits. It runs the CSV diagnostic, the Salesforce workflow and the decision log. Suspended on 2026-11-04, back 200 on 2026-11-10: check /health before calling it live.

Engine: deterministic Python that names its method on every figure and says "insufficient data" rather than guess. Billing levers and the HubSpot adapter are coded, not yet served.

Data: Neon Postgres holds leads, the decision log and connection settings, every read filtered by tenant. Deal rows are processed in memory, never stored.

LLM: Anthropic Claude writes narrative and suggests column mappings. It never computes, rounds or chooses a number.

Infra: GitHub with CI and uptime checks. No warehouse: Snowflake and dbt are proposed, not built, not needed yet.

2. What the audit-first motion uses with no new code

Spreadsheets: each audit is done by hand, one encrypted workbook per customer, every step logged so the method log becomes the spec.

The existing diagnostic: when the customer also sends a CRM export, the live leakage diagnostic adds the discounting half of the readout unchanged.

The data request: billing export, cost export, written declaration, key map. No file is accepted until counsel signs the cost addendum (PK-96) and entity, insurance and engagement letter exist.

3. What the AI margin wedge adds, in build order

Cost-export grain, profile and intake (PK-99 to PK-101): recognise a provider or hosting cost export, load it with declaration and key map. 6 half-days.

Margin-health module and planted-answer tests (PK-102, PK-103): result per account, heavy-user break-even, cost per unit, cost-plus and storage trends, tested against planted answers to the cent. 22 half-days.

POST /billing/margin (PK-104): billing, cost and confirmations in, labelled figures out, no row stored. 6 half-days. The board calls it /margin/analyze; fix one name before build.

Engine subtotal: 34 half-days, about 17 working days, critical path 12.

The /margin readout (PK-105): every figure with its label, unallocated cost shown. Not yet estimated.

The calculator page at /margin-audit (PK-107 to PK-110): browser-only arithmetic on typed numbers. 7 half-days plus 0.25 for the privacy sentence. Waits on the email-gate question.

The cost connector, later (PK-106): specified only after two delivered audits show what customers export. No estimate until then.

4. Rules the stack enforces that marketing must not contradict

Labels (ADR-006): cost from a CRM is "cost proxy, not margin". The site never promises gross margin, because no connector we operate reads verified cost yet.

Declared cost (ADR-007): an uploaded cost export earns "contribution margin, customer-supplied cost basis" only with the customer's written declaration that it is their own cost of serving.

Humans in the loop: Pricekeel explains and recommends. A person confirms key maps, allocation rules and every price.

No number from an LLM: every figure comes from tested code with its method named. The model writes the words around it.

Tenant isolation: every stored row is read per tenant. Only aggregates persist, never rows or names. Cost never joins a benchmark.

What never leaves the export: no end-customer name, email or event-level row. Cost arrives as rollups per key per period. Audit files never go to a cloud AI service and are deleted within 30 days of the readout.

Billing alone: billing data gives no win rate, and every billing readout says so first.

5. Build versus buy, still open

Billing connectors: native, not a unified-API vendor. Native Stripe and Chargebee are designed and approved. A unified vendor adds a subprocessor holding customer credentials and likely flattens the usage, commit and credit fields we need (assumed). Audits run on exports meanwhile.

Cost attribution tooling: neither buy nor build. Attribution lives in the customer's own telemetry. If they already run an LLM cost or cloud cost tool, accept its export as one more cost-export preset.

Outreach sending tool: none. Automating the founder's LinkedIn session breaks LinkedIn's terms and risks the account the content plan depends on. Agents prepare, the founder sends. Resend stays transactional.

6. Three technical risks of the margin wedge

Attribution: shared compute and storage have no customer key, so above 20 percent unattributed the result is only an upper bound.

Vendor export formats: provider and cloud cost headers are unverified and change without notice, so each audit confirms them against the real file.

The join key: billing knows subscriptions, cost knows API keys or projects, and only the customer's key map joins them; a wrong map gives a confident wrong answer.
