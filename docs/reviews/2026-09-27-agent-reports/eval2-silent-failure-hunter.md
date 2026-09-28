# Silent-failure re-hunt, 2026-09-27 (tree 00bd935 = main cf37f27 + agent docs)

## Verdict

PR #69 closed every engine-layer finding: reference insufficiency now propagates through leakage, top_leak_deals, hierarchy slices, trend, policy simulation, and CRM guidance, and the CSV path renders it honestly on upload, sample, Streamlit, and copilot. The Salesforce workspace missed the same treatment and fails both ways: it hides real guidance on any segment that fell back to the global reference, and shows a confident $0 on a thin book with no open deals. Both reproduced. Not ready on the CRM surface; ready elsewhere.

## Closed checklist (verified at file:line)

1. Copilot get-or-0 sentinel: `pricing/copilot.py:164-186`, UI `ChatPanel.tsx:574-590`.
2. RAG web tri-state: `rag.py:132-168`, `api/routers/rag.py:203`, `ChatPanel.tsx:540-556`.
3. Copilot except paths logged: `copilot.py:368,434,519`.
4. Matching per-URL status and 5. mapping llm_fallback_failed: unchanged since round 1, still closed.
6. Raw exception text: `api/routers/diagnostic.py:72,96` fixed message; `api/main.py:313-326` logs, fixed 503 text.
7. model coerce count: `pricing/model.py:207-218`, metrics at `:404`.
8. Embedding skip counted: `rag.py:123-138,335-347`.
9. Insufficient reference as 0%: engine `metrics.py:334-345,418-455,642-676,729-755,960-962,1005-1019,1105-1150`, `crm.py:119-141,195-204`; web `UploadClient.tsx:102-125`, `NextActionsBlock.tsx:40-98`, `LeakageBars.tsx:11-66`, `app/pages/1_Diagnostic.py:56-63`.
10. CurrencyBlockedError: handler `api/main.py:329-345` (422, detail + blockers), proxy `api/diagnostic/route.ts:29-45`, shown `UploadClient.tsx:450-454`.
11. Copilot degraded flag in UI: `ChatPanel.tsx:253-254,574`.
12. evidence_version unknown SHA: warning and inputs `api/routers/crm.py:110-140`; `ev:` chip `SalesforceWorkspace.tsx:548`.
13. Doc-store tenant header: `docs/route.ts:22`, `ask/route.ts:24`.
14. Fail-closed 503: `crm.py:157-181` raises in prod (`main.py:138-142`); `salesforce-workspace.ts:44-53` keeps detail; `workflow/route.ts:134-138` forwards; `SalesforceWorkspace.tsx:172` shows it.

## New findings

**1. MAJOR. Workspace hides real guidance on every global-fallback segment.**
`SalesforceWorkspace.tsx:533` tests `/insufficient data/i` on `reference_basis`, but `metrics.py:56` labels a healthy fallback `"global fallback (insufficient data)"` (`:428`). Reproduced: 520-deal book, Enterprise held to 20 closed, open Enterprise deal returns `recommended 0.05`, `below_guardrail False`, `price_to_retain $15,000`. User sees: the red "no recommended discount is shown" banner, Recommended and Retain tiles removed, while the list tags the deal "exception" and the Executive tile sums its price_to_retain; "Accept recommendation" logs a 5% the rep never saw. Fix: compare `reference_basis === "insufficient data"` exactly, or return a boolean `reference_computable`.

**2. MAJOR. Workspace Executive and Pricing tabs show $0 on a thin book.**
`SalesforceWorkspace.tsx:95-101` (no `excess_basis` in the Analysis type), `:517` renders threshold and excess, `:521` renders `top_leak_deals`. Reproduced: 40 closed deals, zero open, `/crm/analyze` returns 200 with `excess_basis "insufficient data"`, threshold 0.0, excess 0.0. User sees: "Reference threshold 0.0%", "Historical excess to investigate $0", empty "Deals to investigate". Fix: add `excess_basis`/`excess_disclosure` to the type and branch like `UploadClient.tsx:115`.

**3. MINOR. Readiness floor disagrees with the engine floor.**
`salesforce-adapter.ts:329` and `crm.py:275` pass at 30 closed deals; `metrics.py:53-54` needs 3 bands of 15. With any open deal `crm.py:195` raises for the whole book, `workspace/route.ts:32-40` returns it as `degraded`, and `SalesforceWorkspace.tsx:297-302` reads degraded as "needs reauthorization". User sees: readiness "no blockers", then a sync error. Fix: emit a readiness blocker from band counts; reserve `degraded` for connection status.

**4. MINOR. Copilot proxy forwards raw upstream bodies.**
`api/copilot/route.ts:24-25` puts the body text in `error` and collapses every status to 502; `ChatPanel.tsx:238-239` prints it. Trigger: LLM 503, or a pydantic 422 echoing the posted analysis. Fix: parse `detail`, forward the status.

**5. MINOR. Salesforce token path swallows causes.**
`salesforce-client.ts:257-260`: revoke failure unlogged, UI says "tokens removed" while the refresh token stays live at Salesforce. `oauth/callback/route.ts:56` folds key, DATABASE_URL, origin, and exchange errors into `token_exchange_failed`, unlogged. A rotated `SALESFORCE_TOKEN_ENCRYPTION_KEY` throws inside `getSalesforceConnection`; `workspace/route.ts:32` retries, gets null, returns WebCrypto's opaque message as a 502. Fix: log a cause code at each site; return `revocation_unconfirmed` from DELETE.

**6. MINOR. Demo tenant cookie race.**
`gate.ts:76-80` mints a new id whenever the cookie is missing or fails verification. On a first visit to `/guidance`, `GuidanceClient.tsx:243` and `DecisionLog.tsx:43` fire in parallel and each mints one; the last Set-Cookie wins and decisions logged under the other vanish. Tampering fails safe to a fresh tenant but is never logged. Fix: mint once in middleware; log verification failures.

**7. NIT.** `metrics.py:1203` (`new_vs_renewal`) and `:1054` (`segment_win_points`) still consume an insufficient global reference; `assist.py:213` narrates `reference_discount=0.000`. Readout and demo only. `/exceptions` returns `persisted` (`governance.py:100`); `DecisionControl.tsx` never renders it.

Not findings: `support_floor` on the guidance page (`GuidanceClient.tsx:183-190,340-346` labels the tile and shows the caveat). `no_discount_on_record` nulls would render "NaN%", but no demo deal reaches it. NaN thresholds serialize to `null`, not a 500 (checked).

Residual risk: no test suite run; Salesforce traced from source, not a live org.
