# Silent-failure re-hunt: fix/agent-eval-findings vs origin/main

## Verdict

Not ready. Five of eight earlier findings are closed at the engine layer, but the headline fix (sufficiency-gated reference) introduced a new, reproduced blocker: on a sparse book the leakage headline says $0 while top_leak_deals, hierarchy slices, policy-simulation union, and live CRM guidance all score every deal against a 0% threshold. The web renders both without any "insufficient data" signal. The CurrencyBlockedError also never reaches the user (500, message lost).

## Closed-findings checklist

1. Copilot get-or-0 sentinel: CLOSED in engine (`pricing/copilot.py:164-186`, `_present`/`_flag_missing`, `Answer.degraded`), returned by `api/routers/copilot.py:61`. PARTIAL at UI: `web/src/components/ChatPanel.tsx:565` still renders "No opportunities cleared the deterministic threshold" when `opportunities` is empty, ignoring `degraded`.
2. RAG web tri-state: CLOSED (`pricing/rag.py:132-168`, `api/routers/rag.py:203`, `ChatPanel.tsx:540-550`).
3. Copilot except paths logged: CLOSED (`copilot.py:387,434,522`).
4. Matching per-URL status: CLOSED (`matching.py:569-586, 747-764`; summary prefix names unread pages). `sources` is not rendered in `competitor-watch/page.tsx`, the prefix text carries it.
5. Mapping llm_fallback_failed: CLOSED (`mapping.py:370-380`), notes flow into LoadReport (`ingest.py:287`).
6. Raw exception text on the wire: OPEN. Moved, not fixed: `api/routers/diagnostic.py:63,85` still `detail=f"Could not read file: {exc}"`; `api/main.py:318` forwards provider error text.
7. model to_numeric coerce count: OPEN, `pricing/model.py:137` unchanged, no count in `metrics`.
8. Embedding None skip: OPEN (nit), `pricing/rag.py:125` unchanged.

## New findings

**1. BLOCKER. Insufficient-data reference leaks as 0% everywhere except leakage().**
`pricing/metrics.py:392-410` (`_hierarchy_reference_table` falls back to `g_ref` with basis "global fallback (insufficient data)" even when g_ref itself is `sufficient=False`), `metrics.py:855` (`top_leak_deals`), `metrics.py:583` (`hierarchy_slice_reference`), `pricing/crm.py:119-138` (`_reference_for_segment`), `crm.py:176-181` (`recommended = min(current, 0.0)`).
Trigger: any book where fewer than 3 real bands each clear 15 closed deals (reproduced with 40 closed deals, 5 bands). Output: `leakage.excess_vs_segment_reference_won = 0.0`, but `top_leak_deals` sums $250K excess, product_line slice $266K, policy union $70.8K, and CRM guidance for a 15% open deal returns `recommended_discount 0.0`, `reference_band "None"`, `price_to_retain $15K`, `below_guardrail False`.
User sees: upload page "Pricing upside to pursue $0, 0% of booked" (`UploadClient.tsx:116-125`, no `excess_basis` in `web/src/lib/api.ts` Leakage type) next to an investigate list of $250K; Salesforce workspace flags every open deal as an "exception", "Recommended 0.0%", "Price to retain" equal to the full discount (`SalesforceWorkspace.tsx:513,536`); LLM board summary narrates `reference_discount=0.000` (`assist.py summary_facts`); copilot reports no leakage opportunity with `degraded=[]`.
Fix: make `reference_discount` insufficiency propagate: `_hierarchy_reference_table`, `top_leak_deals`, `hierarchy_slice_reference`, and `_per_deal_reference` return NaN/None thresholds and zero excess with basis "insufficient data"; `crm.guidance_for_open_deal` must return `recommended = current`, `below_guardrail = None`, and a `reference_basis` of "insufficient data" (or raise `CRMDataError`); add `excess_basis`/`excess_disclosure` to the web Leakage type and render the disclosure instead of $0 on upload, diagnostic, workspace, and copilot.

**2. MAJOR. CurrencyBlockedError becomes a bare 500.**
`pricing/ingest.py:773-782` raises `SchemaError` subclass; no handler in `api/main.py` (only `LLMUnavailableError` at :312); `api/routers/diagnostic.py:88` does not catch it. Reproduced: POST /diagnostic with mixed `$`/`€` amounts returns `500 Internal Server Error`. `web/src/app/api/diagnostic/route.ts:29-32` maps it to "Could not analyze that file. Check it against the template."
User sees: a template error, not the blocker text or the per-currency row counts the exception was built to carry. Fix: `@app.exception_handler(ingest.SchemaError)` returning 422 with `detail=str(exc)` and, for `CurrencyBlockedError`, `report.blockers`; forward `detail` in the web proxy. Note `/crm/analyze` with symbols in amounts returns "0 usable closed opportunities" (`_usable` fails on non-numeric strings), also masking the currency cause.

**3. MINOR. Copilot degraded flag stops at the JSON.**
`ChatPanel.tsx:565`. Trigger: analysis payload missing `leakage`. User sees the confident empty-state card; only the LLM prose (if a provider is configured) mentions degradation. Fix: branch on `data.degraded` and render `degraded_keys`.

**4. MINOR. evidence_version hides "unknown" git SHA.**
`api/routers/crm.py:52-70, 91-102`. On a deploy without `PRICEKEEL_GIT_SHA`/`RENDER_GIT_COMMIT` and no git binary, the hash still looks valid; two different builds hash identically. Nothing in `web/src` renders `evidence_version`. Fix: log a warning when SHA is "unknown", emit the fingerprint inputs alongside the hash.

**5. NIT. Doc-store re-keying is a no-op through the web tier.**
`web/src/app/api/docs/route.ts:19` and `api/ask/route.ts:19` send no `X-Pricekeel-Customer`, so every web session lands under `"default"`. No document loss today, but if either route gains the header alone, /ask silently returns doc-free answers. Fix: return `doc_chunks_available` from /ask and render "no documents found for this session".

**Not findings:** `_strip_deal_level` (placeholder text is explicit; residual: only the first 5 list items are sampled). Memoized reference in `crm.py:263` (same df, same call, no staleness). 503 fail-closed path (`salesforce-workspace.ts:44-53` maps to 502 with detail, `workflow/route.ts:134-138` forwards it, banner shows it).

Residual risk: Streamlit `app/pages/1_Diagnostic.py:56` also shows the $0 headline without disclosure; not traced further. Tests were not run.
