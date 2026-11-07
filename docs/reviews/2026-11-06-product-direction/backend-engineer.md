# Backend engineer: deterministic engine and API perimeter

Summary: the engine is already source-agnostic below `pricing/crm.py`, but the workflow, audit log and book-per-request contract are Salesforce-shaped; a neutral decision contract plus a Salesforce-as-first-adapter refactor is about 9 days, while commit/ramp/overage scoring (about 14 days) and margin (about 14 days) are separate, later increments that each need a data-engineer or ai-engineer dependency.

## 1. Findings

**Coupling today.** Three layers, different depth.
- Engine core is clean. `ingest_frame_verbose` (`pricing/ingest.py:836`), `metrics.*` and `diagnostic.analyze` take a canonical frame (`pricing/schema.py` FIELDS) and know nothing about Salesforce. The CSV path already proves it.
- `pricing/crm.py` is the adapter in disguise. It hardcodes `source="live Salesforce opportunities"` (line 58), the `currency_iso` and `salesforce_url` keys, `outcome == "open"`, Salesforce wording in every `CRMDataError`, and the 30 closed-deal floor inline (line 281). It also owns the guardrail logic (`guidance_for_open_deal`), which is engine, not adapter. These two jobs need separating.
- The API and audit log are the deepest coupling. `api/routers/crm.py` writes `payload["source"] = "salesforce_crm"` and a separate `"salesforce_crm_writeback"` source. `pricing/governance.py:459-496` decides what counts as an exception request by matching those exact strings. The event set (`flagged, accepted, override_requested, approved, rejected`) is neutral, but the history query filters `source="salesforce_crm"`, so a second source would be invisible to the approval state machine.

**Structural problem for deal-time surfaces.** `/crm/workflow` takes the whole book (`records`, up to 10,000) on every call and recomputes the reference (500-sample bootstrap) each time. That works for a Next.js server that just ran SOQL. It cannot work for a Slack button or a quote screen, which have one deal and no book. A live decision request needs a stored derived artifact (reference tables, band stats, model), not rows. The rule "row-level data processed in memory and deleted" permits aggregates, but `_comparables` (`crm.py:144`) returns named account rows. A snapshot must drop or anonymize comparables. This is a founder-visible tradeoff (open question 1).

**UBP is captured, not scored.** `schema.py` already has `committed_acv`, `overage_rate`, `ramp_year_1/2_acv`, `renewal_uplift`, `cogs_acv`. Nothing in `metrics.py`, `crm.py` or the model features (`model.py:121-124`: five categoricals plus list_acv, discount_pct, term, quantity, quarter-end, competitor) reads them. Every verdict is `1 - booked/list` on one number, which is what the panel flagged. `cogs_acv` is a customer-declared annual cost, not margin truth.

**Supports the direction.** Auth, SOQL and tokens already live in the Next.js tier (`api/routers/crm.py` docstring), so the Python side already receives canonical rows. Evidence versioning, the self-approval block, fail-closed 503 on log failure, and the insufficient-data refusals (`crm.py:105-143`, the `analyze_records` blocker) are reusable unchanged.

## 2. What would have to change

### 2a. Deal source adapter (about 9 days, includes the first increment)
Engine boundary = `CanonicalDeal` (schema.py fields plus `source: {system, tenant_ref, record_id, url}`) in, `DecisionResponse` out. Adapters never import the engine; the engine never imports adapters.

```
class DealSourceAdapter(Protocol):
    system: str                                   # "salesforce", "dealhub", "stripe", "manual"
    def field_map(self) -> FieldMap               # source field -> canonical, versioned, per tenant
    def to_canonical(self, raw) -> CanonicalDeal  # pure, no network
    def history(self, since) -> Iterable[raw]     # closed deals, bounded
    def open_deal(self, ref) -> raw               # live fetch for one deal
    def write_back(self, decision) -> WritebackResult   # idempotent, may be a no-op
    def outcomes(self, deal_refs) -> Iterable[Outcome]  # for reconcile
```
Where it runs: network adapters stay in the web tier (auth stays out of Python); Python gets `to_canonical` for file-based sources (the CSV mapper in `pricing/mapping.py` is already adapter #0). Billing platforms are history and outcome sources (invoices, usage), not quote surfaces: `write_back` is a no-op and `history` supplies the usage and commit actuals that make lever scoring possible. Say so in the contract rather than pretending all methods apply to all sources.
Concrete edits: split `crm.py` into `pricing/guardrail.py` (engine) and a thin Salesforce `to_canonical`; replace the two source strings with `source.system` and keep reading the legacy values as aliases so old decision-log rows stay valid; move the 30-deal floor to one constant. The `schema.py` change is the data-engineer's (1 day dependency).

### 2b. Scoring commit, ramp, overage (about 14 days)
Inputs per deal: `committed_acv`, list and quoted overage rate, ramp schedule (year 3 = `booked_acv` convention stays), term, `usage_acv`, and for history the realized usage versus commit (billing adapter).
Outputs, as separate levers, never one blended number:
- Commit discount: `1 - committed_acv / list_commit`.
- Rate discount: `1 - overage_rate / list_overage_rate`.
- Ramp-adjusted effective discount: TCV-weighted, `1 - sum(year_acv) / (list_annual * term_years)`, so a back-loaded ramp stops reading as a flat 15%.
- Context, not a verdict: utilization risk (expected usage over commit). It is a declared input until billing history supports it.

Win model and guardrail: the interpretable path is a per-lever reference table with the same band-support rule as `metrics.reference_discount` (3 real bands, 15 deals each). The LightGBM model (ai-engineer's `model.py`) gains lever features only after the book has them populated; until then it keeps scoring `discount_pct`, redefined as the effective discount. That model change is a stop-and-report dependency (about 3 of the 14 days sit with the ai-engineer).
"Insufficient data" extends per lever: each lever returns `{status: scored | insufficient_data | not_provided, basis, band_counts}`. A deal with commit data but no rate history is scored on commit and explicitly unscored on rate. No fallback to global for a lever with no history. The response lists scored and unscored levers side by side.
Effort split: effective-price math plus fixtures 3d, per-lever reference and sufficiency 4d, response and audit shape 2d, model features (ai-engineer) 3d, hardening 2d.

### 2c. Margin layer (about 14 days; BOM, landed cost and tax detail adds 4)
Cost does not belong on the deal row. Add a versioned, tenant-supplied `CostBook`: unit cost per SKU (effective-dated, so a token-cost curve is a series, not a constant), BOM lines (component, qty, unit cost, scrap %), landed-cost rules by ship-to (freight, duty rate, insurance), tax treatment per jurisdiction (pass-through sales tax excluded from revenue; duty and non-recoverable VAT as cost). Storage and ingest are the data-engineer's (`neon/**`, `schema.py`); computation is mine in `pricing/margin.py`.
Computation is `Decimal`, pure and traceable:
- Net revenue = booked value less pass-through tax.
- Gross margin = net revenue minus product cost (BOM or unit cost times quantity, over the term).
- Net (contribution) margin = gross minus landed logistics, duty, non-recoverable tax, and declared variable costs (payment fees, commission).
- Every output carries its cost lines, the cost-book version, and a `missing_costs` list. Any missing line makes margin `null` with `insufficient_cost_data`; zero is never filled in.
- Margin floor enters the guardrail as a third cap: `recommended = min(current, win_reference, margin_floor_discount)`, where the floor discount solves `(list*(1-d) - cost) / (list*(1-d)) = target`. Both inputs are shown; the margin floor never overrides a human.
- Token deflation: the user declares a cost trajectory and the engine applies it. We do not forecast cost. Output is labeled scenario.

**Boundary, in code.** Every margin figure carries `basis`: `crm_proxy` (no cost, so no margin field at all), `declared_cost` (customer typed or uploaded cost, unaudited, rendered "estimated gross margin from declared cost"), `erp_verified` (cost from a billing or ERP connector with provenance; the only basis allowed the bare word "margin"). Enforce with a response builder that owns the copy, plus a test that scans every payload for the word. `cogs_acv` maps to `declared_cost` today.

### 2d. Surface-agnostic contract (about 7 days; Slack adapter is separate, web tier)
`POST /v1/decisions` request:
`{request_id (idempotency key), surface: slack|email|overlay|quote_screen|api, source{system,tenant_ref,record_id}, deal: CanonicalDeal, levers: [commit|rate|ramp|discount], book_ref (snapshot id), actor{id, assertion: self_asserted|surface_verified}, cost_book_ref?}`
Response: `{decision_id, status: ok|insufficient_data|blocked, verdict{method, levers[{lever, status, current, recommended, reference, basis, band_counts}], margin?{basis, gross, net, cost_lines, missing_costs}}, why[{code, template_id, inputs}], caveats[], evidence_version, allowed_actions[], expires_at}`
Rules: no surface-specific fields; surfaces render `why` and `allowed_actions` themselves. `POST /v1/decisions/{id}/actions {event, actor, justification, action_token}` reuses the existing event machine and self-approval guard. A Slack button carries a short-lived signed action token; Slack's signed user identity can raise `actor_assertion` to `surface_verified`, which is more than today's `self_asserted` and a real audit improvement. The browser overlay depends on DOM scraping per host app, so it is the weakest surface; treat it as an adapter, not a contract concern. The quote screen is `source.system = "manual"` and is stamped as such. Keep `/crm/*` as a compatibility shim over the new path until the web tier migrates.

## 3. Risks and tradeoffs
- The book snapshot is the real design cost (about 4 days) and the one rule-adjacent decision. Without it only the Salesforce server path works.
- Five adapter classes against zero users is speculative. Build the interface and two implementations (Salesforce, manual/CSV) only; add a third when a design partner's tool demands it.
- Lever scoring is data-starved: most CRMs hold only the amount. Expect `insufficient_data` or `not_provided` on rate and ramp for most partners. That is honest, but it makes the demo weaker than the pitch.
- Margin is the highest-liability surface. A wrong BOM or tax rule yields a confident wrong number on a price-affecting screen. Ship it as declared cost with a visible trace, not as a verdict, and not before a physical-goods partner exists (Phase 3 is gated on the SaaS wedge paying first).
- Scope creep: 2b, 2c and 2d total about 35 days of backend work (about 45 with the BOM detail and cross-cutting tests) against a solo founder whose critical path is a paid pilot. Only 2a is justified before a partner signs.

## 4. Recommended first increment (about 9 days)
Neutral decision contract plus Salesforce as the first adapter, with a manual/CSV adapter as the second.
1. Split `crm.py` into engine (`guardrail.py`) and Salesforce `to_canonical`; one source tag scheme with legacy aliases (3d).
2. `BookSnapshot` of derived aggregates, comparables anonymized, keyed by evidence version (3d, after founder answer 1).
3. `POST /v1/decisions` and `/actions` with the contract above, `/crm/*` as shim (2d).
4. Read-only effective-discount decomposition (commit versus TCV-weighted ramp), shown but unscored (1d).

Why this slice: a design partner on Pipedrive or DealHub can send a CSV of closed deals and one open quote today and see the same guardrail and audit trail, which tests neutrality (the defensibility claim) with no new integration. It touches no margin and no model code. Dependency: data-engineer for the `source` field in `schema.py` and a snapshot table (about 1 day).

## 5. Test strategy
- Adapter contract tests: one shared suite every adapter must pass (idempotent `to_canonical`, bounded history, no-op writeback allowed). Golden fixtures per source, extending `tests/test_format_fixtures.py`.
- Regression: all existing `tests/test_crm.py` and governance tests stay green through the shim; legacy decision-log rows still resolve.
- Lever math: property tests (TCV-weighted discount between the min and max annual discount; flat ramp equals flat discount; monotonic in price).
- Insufficient-data matrix: per lever and per combination, assert status and that no global fallback leaks.
- Margin: Decimal golden cases (BOM with scrap, duty by ship-to, pass-through versus non-recoverable tax); missing cost yields null, never zero; boundary test that no payload says "margin" unless `basis = erp_verified`.
- Contract: JSON-schema snapshot of request and response; idempotency on `request_id`; self-approval and fail-closed 503 preserved; a test that no row-level data persists in the snapshot.
- Cross-cutting test time is about 4 days on top of the figures above.

## 6. Open questions for the founder
1. May we persist a per-tenant derived snapshot (reference tables and band stats, no rows, no named comparables)? Without it there is no Slack or quote-screen path.
2. Is the first design partner's tool known? It picks the second adapter and decides whether billing-actuals ingestion (utilization) comes before lever scoring.
3. Is margin for the SaaS ICP (declared infra or token cost, no BOM) the target, or only for the Phase 3 physical-goods adjacency? The first needs about 6 days, the second the full cost book.
