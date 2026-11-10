# Audit-first motion and AI margin wedge: founder decisions

Date: 2026-11-10. Lead: pk-lead (Claude). **Status: decided 2026-11-10. The founder accepted every recommendation below ("go with your recommendations on all founder decisions"). Each F item's recommendation is now the decision.** Source instruction: "start on both the filled tabs. that's what we need to do."

Everything below was produced today from the two filled tabs of the founder research sheet. Each decision lists the inputs that bear on it and the lead's recommendation. Nothing on this list has been applied to the site, the price or the product. Work that does not depend on a decision has started or is queued on the board (PK-94 to PK-111).

## What was produced today

| Area | Artefact | Owner |
|---|---|---|
| Research | `gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md` (verbatim transcription) | lead |
| Decision record | `vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md` (local vault) | lead |
| Paid audit | `gtm/ai-margin-audit-offer.md`, `gtm/ai-margin-audit-runbook.md`, `gtm/ai-margin-audit-data-request.md`, row in `gtm/data-readiness-checklists.md` | customer-success |
| Interviews | `gtm/ai-founder-interview-module.md`, `gtm/ai-founder-targets.md`, `gtm/ai-founder-outreach-sequence.md`, objections 11 to 18 in `gtm/objection-inventory.md` | sales-outreach |
| Content | `gtm/content/2026-11-linkedin-ai-pricing-bottlenecks.md` (8 posts, 2 teardown outlines, do-not-post list) | social-media-manager |
| Critic reviews | `docs/reviews/2026-11-10-audit-first/pricing-strategist-review.md`, `cfo-review.md` | pricing-strategist, cfo |
| Design | `docs/design/2026-11-10-ai-margin-audit-calculator.md`, `docs/design/2026-11-10-margin-health-analysis.md` | web-engineer, backend-engineer |
| Board | `docs/reviews/2026-11-10-audit-first/TASKS-proposed.md`, PK-94 to PK-111 registered, ADR-007 proposed in `docs/agents/DECISIONS.md` | pk-lead |

## Decisions

### F1. Margin computation (the open D2): compute contribution margin only
Inputs: ADR-006 labels a customer-supplied cost basis "contribution margin, customer-supplied cost basis" and reserves "gross margin" for ERP-verified cost through a connector. The sheet's audit promise says "gross margins". Both design docs and the runbook can only ever say contribution margin on an uploaded cost export.
Recommendation: answer D2 narrowly. Contribution margin per customer per period on declared cost, never gross or net margin. Change the audit offer's promise sentence to match before it is shown to anyone.

### F2. Accept ADR-007
Inputs: ADR-006 read literally files any CSV cost under `crm_proxy`, which would forbid the word margin on an uploaded cost export and make the wedge connector-only. ADR-007 makes `declared_cost` earnable by one explicit declaration at upload, joins cost to billing only through a customer-declared key map, and reports unmatched cost as an unallocated line.
Recommendation: accept. It is the "supplied in writing" act ADR-006 already allows, at the right grain.

### F3. ICP: keep the decided band, scope the AI wedge inside it, treat seed stage as a learning segment

**Correction 2026-11-10 (lead):** the band is $10M to $100M ARR, gated on deal volume, per vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md, which supersedes the 2026-08-01 note and calls "$20M to $100M" drift. The PR 91 lead decision and the PK-76 social card reintroduced that drift on the pricing page and the social card; PK-112 restores $10M to $100M and pins a site-wide test. Every "$20M to $100M" below reads "$10M to $100M".
Inputs: the sheet proposes seed-to-Series-A AI agent startups with negative gross margins. The strategist calls that a pivot, not a narrowing: seed companies cannot clear the engine's deal-volume gates, most cannot split inference cost by customer, and the Consumer Trends thesis (labor budgets, procurement, outcome contracts) describes Series B and later AI-native companies inside the current band. The CFO estimates the seed ICP shrinks the five-year SOM roughly three times and that reaching 1M ARR at 30K ACV with seed-stage churn needs more customers than the whole SOM. The 2026-05-29 decision already ruled "stay narrow".
Recommendation: keep the $10M to $100M ARR band, gated on deal volume, on the site (see the correction above). Define the AI margin wedge ICP as AI-native usage or hybrid companies inside that band. Use seed-to-Series-A founders for interviews and paid audits only, as the fastest way to learn, not as the product's target. Record the ICP sentence in the vault before any site copy changes.

### F4. Audit price: fixed fee, 7,500, paid upfront
Inputs: CFO break-even at a 150 an hour founder rate is about 7,500 for a 50 to 72 hour hand-run audit; a 2,500 fee loses 5,000 to 8,300 per audit. Strategist: 5K to 10K, credited against year one. Customer-success: test 6,000, no credit on the first two to keep the willingness-to-pay signal clean, drop to 4,500 if three of five qualified prospects decline on price.
Recommendation: 7,500 fixed, upfront, clock starts at validated intake. No credit on the first two audits. Decide credit terms per deal after the third audit, when the subscription exists. If three of the first five qualified prospects decline on price, test 6,000 and record why.

### F5. No share-of-lift in the first audits
Inputs: all three reviewers agree. Attribution on a historical audit is disputable; the strategist's gate is a finance-signed per-customer margin baseline at constant input unit prices, which does not exist yet.
Recommendation: no. Revisit only after one audit has produced that baseline.

### F6. Do not publish 2,500 a month yet
Inputs: 2,500 a month passes the value test for a Series B buyer and fails a seed founder's reference price. The pricing page already says "low five figures" annually, which 30K a year matches. The strategist's structure: Monitor near 1K to 1.5K a month, Operate at 2.5K to 4K by revenue under management.
Recommendation: leave the pricing page as it is. Price the subscription after the first audits show real ACV and retention.

### F7. Landing hero unchanged; the wedge lives on its own page
Inputs: the strategist warns of a fourth wedge diluting positioning; the content agent's series stays on the current through-line.
Recommendation: no change to the landing page. The AI margin wedge gets `/margin-audit` (calculator) and later `/margin` (workspace readout).

### F8. Calculator gate: result free, breakdown and audit request behind the email
Inputs: the sheet's lead-magnet model; the calculator design defaults to gating only the per-group breakdown, the price-drop table and the audit request; the site-wide synthetic-data disclosure is false on that page and needs a third variant ("Your inputs, not Pricekeel data"); the privacy sentence waits on the legal chain (PK-52, PK-62, PK-69, PK-82).
Recommendation: accept the design default. The gate does not ship before the privacy chain lands.

### F9. Retire the sheet's ten-word line
Inputs: "We stop AI companies from losing money on heavy users" is judged a promise the product cannot keep that also blames the customer's best users. Candidates: "Know your cost to serve before you choose a unit." (content, claims nothing about Pricekeel) and "See which customers cost more to serve than they pay" (strategist).
Recommendation: "Know your cost to serve before you choose a unit." for content. No product line changes until F3's ICP sentence is recorded.

### F10. Reject the "autonomous outcome engine" label
Inputs: the Labelling tab's one line. The product is explainable decision support with humans in the loop; "autonomous" contradicts the mental model and the enterprise buyer's trust requirement the Consumer Trends memo itself describes.
Recommendation: reject.

### F11. No real cost files until counsel, the entity and insurance are in place
Inputs: per-customer cost rollups fall outside the NDA data addendum's Schedule A as drafted (Class 3 is a rate table only). The entity is not formed, counsel review is pending, insurance is not bound, no engagement letter exists.
Recommendation: accept no customer cost data until PK-96 (data class and register) is done and counsel has signed the amendment. Interviews and the calculator do not need customer data and can proceed.

### F12. Engine defaults
Inputs: margin-health design. Allocation rule for shared cost: none by default, shared cost stays `not_attributable` until a rule is confirmed per pool, never proportional-to-invoiced by default. Unattributable cost above a 20 percent cap: mark the readout `upper_bound` rather than block; negative-account findings are stated in full because missing cost can only worsen them.
Recommendation: accept both defaults. They are built in so work can start.

### F13. Sequence the 30-day checklist
Inputs: the CFO estimates 227 to 330 founder hours against about 200 available. Sales-outreach expects 4 to 8 interviews from 40 cold candidates, so plan 60 candidates or warm paths for a third.
Recommendation: weeks 1 to 2 interviews and the content series; weeks 2 to 4 the first paid audit (offer, data request, legal gate); the calculator build (PK-107 to PK-110) in parallel by the web-engineer; the three-screen prototype is the calculator page itself (PK-111), not a separate mock. Three hand-run audits before any automated audit build (CFO).

### Founder-only inputs still missing
- The `{{credibility_line}}` in the outreach drafts. Nothing truthful can be invented for it.
- The interview geography list.
- A sample of real OpenAI and Anthropic usage export headers. No vendor CSV is documented; the engine design used the cookbook page and needs a founder sample.
- Whether to use the content agent's proposed edits to `vault/GTM/linkedin-strategy.md` (its 90-day algorithm re-verify was due 2026-08-28).

## What starts without any decision
- PK-94 (predicted objections) is READY.
- The content series can be scheduled from the file once you approve the posts; the agent never publishes.
- Interview outreach can begin once the credibility line and geography are supplied; nothing is sent by an agent.
- Calculator formula module (PK-107) and the planted-answer key for margin health (PK-99) can start on F12's defaults; everything that says "margin" waits on F1 and F2.
