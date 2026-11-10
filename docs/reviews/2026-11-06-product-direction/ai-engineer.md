# AI layer: the mapper generalizes only with a new shape layer, usage forecasting is statistics not ML, and every new number needs a named method

Reviewer: AI / pricing-intelligence engineer. Read-only review of pricing/mapping.py, matching.py, model.py, copilot.py, rag.py, assist.py and tests/.

## 1. Findings

**Mapper (pricing/mapping.py).** A one-header-to-one-field cascade (synonyms, rapidfuzz, bge-small, then a Haiku call on unmatched header strings) over a flat, one-row-per-opportunity table. The privacy contract (headers only), the claim-once rule, the subset-of-input guard and the `used` audit trail all generalize. The table-shape assumption does not.

What breaks, by source:
- **CPQ quote lines (DealHub, PandaDoc, Salesbricks):** one row per line item. `Quantity`, `Net Price`, `SKU` all map, but nothing rolls lines up to a quote, so `booked_acv` becomes a line amount and `discount_pct` is silently wrong. CPQ also has quote status (sent, viewed, signed), not win/loss; `status` is a layer-1 synonym for `outcome` today.
- **Billing invoices (Stripe, Chargebee, Maxio):** `amount` is a layer-1 synonym for `booked_acv`, but invoice amounts are per period, often minor units (Stripe cents), and include tax and proration. Correct by name, wrong by meaning. Invoice `status` (paid, void) is not deal outcome. No unit or scale layer exists.
- **Usage events (Metronome, Orb):** event grain, millions of rows, no commercial fields. This is an aggregation problem, not a mapping one: events to monthly consumption per customer per meter, aggregated in memory and discarded.
- **Other CRMs (Pipedrive, Zoho, Close, Attio, Freshsales):** closest fit. Synonyms need extending, but the real risk is customer-defined stage names (value normalization, not header mapping). I did not verify how ingest treats unknown stage strings; that is the first eval.
- **Latent collisions:** `cost` maps to `cogs_acv` (a BOM unit cost would be mislabelled as annual COGS), `plan` to `product_tier`, `quantity` to seats.

**Model (pricing/model.py).** LightGBM, native SHAP, `discount_pct` monotone +1, time-ordered holdout, support-floor labels, all built for one lever: percent discount on annual committed value. Features have no commit, ramp, overage or unit-price terms; those schema fields are captured, not scored.

**LLM layer.** Guardrails transfer: bounded timeout mapped to `LLMUnavailableError`, env-var model ids, `_strip_deal_level`, citations. Gap: tests assert the prompt forbids invention (tests/test_copilot.py, tests/test_assist.py), but no eval checks that narrated output only contains numbers from the source dict.

## 2. What would have to change

**A. Mapper "layer 0": source profile.** Before header mapping, classify the file (crm_opportunity, cpq_line, billing_invoice, usage_event) from header fingerprints by deterministic rules. Each profile carries a synonym overlay, a grain and roll-up rule, an outcome-value map, unit rules, and a list of fields it can never supply. `status` then means outcome in a CRM profile and nothing in a billing profile. Add a refuse path ("this export cannot supply outcome, add the CRM export") instead of guessing. Cross-source joins (quote to invoice to deal) are deterministic key joins, never LLM.

**B. Usage-native modelling.**
- *Deterministic statistics (first):* consumption per customer per meter, trailing growth and volatility, commit attainment, overage incidence and revenue share, ramp-vs-actual drift, realized unit price vs list.
- *Interval forecasting, still statistics:* consumption as P10/P50/P90 (log-growth with empirical residual quantiles, or ETS via statsforecast). Unit cost deflation (token prices fall in steps at model releases) cannot be estimated from a short history, so it ships as a user-set scenario parameter, labelled a scenario, never a prediction.
- *ML:* only the win model, and only with enough closed usage deals. Today that is zero.
- *Monotone constraints for commit and overage:* P(win) non-decreasing in each discount lever (commit discount, ramp discount) and non-increasing in overage rate. Add one the discount model does not need: P(win) non-increasing in commit size at fixed price. Larger commits correlate with bigger, better-qualified buyers, so an unconstrained model learns "bigger commit, more wins" for the same endogeneity reason it learned "discount, fewer wins". LightGBM per-feature constraints make this cheap. Cohort support thins fast across several levers, so `band_guardrail` will dominate for a long time. That is the honest output.
- Hybrid EV = P(win) x (committed + P50 overage forecast x rate). The overage term is a forecast and must be labelled one everywhere, same discipline as `price_retained` vs `uplift`.

**C. Traceable margin and value guidance.** A stack of independently named methods, each its own key with its own caveat, never a fused score:
1. `landed_cost_arithmetic`: BOM plus freight by lane plus duty and tax treatment, from user-entered inputs, gross and net margin by arithmetic. A `cost_basis` enum (`erp_billing`, `user_supplied`, `crm_proxy`) drives label text in code, so copy cannot say "margin" when basis is `crm_proxy`. A typed BOM is "user-supplied cost", never "true margin" until billing or ERP data backs it.
2. `evc_calculator`: Nagle economic value to the customer, with user-entered reference price, differentiation value and quantified benefit. Output is a ceiling range with every input named.
3. `win_curve`: the existing monotone model over the lever vector.
Guidance is a corridor: floor from 1, ceiling from 2, win-curve position from 3. If the floor exceeds the ceiling, say so; that is the finding. A single fused "optimal price" is the black box the product forbids.

**D. LLM boundary.** Narrates: the corridor, its three sources, caveats, next question. Maps: header strings, stage strings into a closed enum validated against distinct observed values, and quoted text from notes with span citation. Never computes: any margin, EVC, forecast, uplift, freight or tax figure, and never picks the cost basis. v1 tax is a user-entered rate or exempt flag, stated as not tax advice.

## 3. LLM value and liability on new surfaces

| Surface | Adds value | Liability |
|---|---|---|
| Slack | Narrating a precomputed card; "why" from the decision record with citations; approver summary | Free-form "what should I quote" without structured inputs; async needed past Slack's 3s ack; thread content is customer data |
| Email | Drafting approval or justification text from the decision record | Parsing inbound email for terms: untrusted, prompt-injectable, row-level. Validate against a schema and confirm with the human |
| Browser overlay | Identifying which fields to prefill from labels | Scraping deal values from a CPQ or CRM page to the provider is row-level data leaving the process. Send labels only |
| Quote screen | Structured form, deterministic guidance, narration | Minimal; safest first surface |

Rule: new surfaces send the provider only aggregates already in our system or header-like strings.

## 4. Risks and tradeoffs

- Pilot critical path: all of this is premature without a design partner. Mapper profiles and the quote-screen corridor have the best ratio; usage forecasting and multi-lever win models need data nobody has.
- Multi-lever win modelling on thin data yields confident-looking noise; default to guardrails and comparables.
- Value-based pricing from LLM-extracted customer statements invites hallucinated dollars; numeric input is human-typed or confirmed.
- Provider cost: deterministic pieces add none. Narration is one Sonnet-tier call per card, header and stage normalization Haiku-tier and cacheable per file shape. My estimate (not measured) is under a cent per upload and a few cents per card. Every call site inherits `LLM_TIMEOUT_SECONDS` and the 503 mapping.

## 5. Eval plan and effort (days)

| Eval | Asserts | Days |
|---|---|---|
| Per-source mapper fixtures (4 profiles, 3 anonymized exports each) | Profile detected; grain detected; refuse path fires; no claimed header absent from input; captured LLM payload holds headers only | 3 to 4 |
| Stage normalization | Closed enum; unknown stage goes to "ask user", never defaults to lost | 1.5 |
| Unit and scale rules | Stripe-cents and per-period fixtures annualize to known totals | 1 |
| Numeric-fidelity for narration (reusable) | Every figure in generated text appears in the source dict | 2 |
| RAG citation | Every sentence carrying a figure has [A], [D#] or [W#] | 1 |
| Cost-basis label | "margin" never appears when basis is `crm_proxy` | 1 |
| Usage statistics | Synthetic series recover growth, attainment, overage share; thin history returns "insufficient data" | 3 |
| Forecast coverage | Held-out P10 to P90 covers about 80 percent | 2 |
| Multi-lever monotonicity | Sweeping each lever on random deals obeys each constraint | 1.5 |
| Injection on email or notes extraction | Adversarial fixtures leave schema and numbers unchanged | 1.5 |

Build effort: mapper profile layer 8 to 10; cost-basis enum plus landed-cost margin 4 to 5; EVC calculator plus corridor card 4; consumption statistics plus interval forecast 6 to 8; multi-lever win model 5 (needs data that does not exist); Slack and email narration plus fidelity harness 3.

## 6. Recommended first increment

The numeric-fidelity and cost-basis eval harness plus the mapper's source-profile layer for CPQ lines and other-CRM exports: profile detection, line-to-quote roll-up, stage normalization with a refuse path. About 8 days. It moves "add-on to any platform", needs only anonymized export fixtures, adds no provider spend, and installs the guardrail every later surface depends on. Defer billing and usage events, multi-lever win modelling, and email or overlay LLM use until a partner supplies real data.

## 7. Open questions for the founder

1. Can any design partner share an anonymized quote-line or billing export within two weeks? Without a real one, shape detection is guesswork and the increment shrinks to the eval harness.
2. Is the first AI-native target's pricing hybrid with a committed floor, or pure pay-as-you-go? Pure PAYG removes the commit-constraint work.
3. Who supplies cost for margin guidance: a pricing lead typing unit cost, or an ERP or billing feed? That decides whether `cost_basis` can be `erp_billing` in v1.
