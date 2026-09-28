# Pricekeel QA gate re-evaluation, 2026-09-27

Working tree 00bd935 (main cf37f27 plus agent-org docs). No tracked file modified.

## Verdict: PASS

- Python, run 1: 456 passed, 0 failed, 117.34s. Run 2: 456 passed, 0 failed, 102.89s. Identical outcomes, no flakiness. Command: `venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` with PYTHONUTF8=1. Up from 279 on 09-26.
- Web: `npm test` 8 files / 33 passed (was 11); `npx tsc --noEmit` clean; `npm run lint` clean; `npm run build` compiled, 40/40 static pages, no secrets present.
- CI, main: run 36295033618 success (PR #69 merge, 2026-09-27). Prior: 35639040441 (weekly-digest), 35029845998 (PK-15). Current branch: 36336030037 push and 36336032275 PR, both success.
- Live smoke: 9 of 9 checks behaved as specified; 0 tracebacks, 0 HTTP 500 in the uvicorn log (37x200, 1x404, 2x422, 2x429).

## Smoke table (dev mode, all LLM and search keys blanked, port 8765)

| Endpoint | Expected | Got |
|---|---|---|
| GET /health | 200 | 200, `{"status":"ok","llm":false}` |
| POST /diagnostic deals.csv | 200, leakage.excess_basis | 200, excess_basis present plus excess_disclosure, segment_references |
| POST /diagnostic mixed_currency.csv | 422 with blockers | 422, detail names EUR 90 / USD 210 rows and the fx_rates remedy, `blockers` list present |
| POST /recommend OPP-00000 | method and caveat keys | 200, method=modeled_ev_curve, caveat present, rec=0.0902 |
| POST /crm/analyze, 39 closed + 1 open | 422, not a 0% guardrail | 422, "no 3 real discount bands each clear 15 closed deals", band counts listed |
| POST /crm/analyze, 40 closed + 0 open | (variant) | 200, guidance=[], reference_discount.sufficient=false, excess_basis="insufficient data". Honest, no number quoted |
| POST /ask, no provider | clear not-configured answer | 200, "The LLM provider is not configured on this server.", web_status=off, one [A] citation |
| POST /recommend x31 in 3.7s | 429 after 30/60s | request 31 = 429, Retry-After 53, detail names the rule |
| POST /recommend unknown id, other tenant header | 404 | 404 (also confirms the limiter is customer-keyed) |

## Findings

1. [Low] `reference_discount.reference_threshold` is `0.0` when `sufficient=false` (pricing/metrics.py reference block, seen on the 40-closed book). Any consumer that reads the number without the flag sees a 0% reference. The web and CRM paths do check the flag; a null would be safer than a sentinel zero.
2. [Low] `tests/test_api_perimeter.py:149` `test_small_upload_passes_size_middleware` took 46.22s in run 1 and 13.66s in run 2. It posts a 3-cell CSV to /map-headers and pays the embedding-model load. Cheapest fix: monkeypatch the embedding layer or mark it so the perimeter check does not carry a model cold start.
3. [Low] `neon/test_migrations.py` (7 tests, up/down pairing) is not collected by the root `pytest -q` run and so not by CI (`.github/workflows/ci.yml:28`). It only runs when named explicitly. Add `neon` to testpaths or move the file under `tests/`.
4. [Low] Router modules with no test file importing them: `api/routers/diagnostic.py`, `rag.py`, `copilot.py`, `governance.py`, `matching.py`, `perimeter.py`, `api/shared.py`. They are exercised through `api.main` route tests, so this is a mapping gap, not a coverage hole. Routes with zero literal test references: `/demo`, `/model`, `/matching/context`.
5. [Low] Web `src/lib` with no test: `salesforce-crypto.ts` (encrypt/decrypt only reached via oauth and store tests), `salesforce-workspace.ts`, `leakage.ts`, `magic.ts`, `notify.ts`, `ratelimit.ts` has one. `leakage.ts` and `magic.ts` are trust-relevant and worth direct tests.
6. [Info] `web/.next/` is present locally again; tsc passed this time, but the 09-26 stale-artifact hazard still has no `pretest` hygiene step.

## Tests slower than 5s

Run 1: only `test_small_upload_passes_size_middleware` (46.22s). Run 2: that test (13.66s) plus four `tests/test_model.py` sweeps at 10.29, 8.59, 7.39, 6.60s (`test_no_recommendation_lowers_discount_while_raising_win_prob`, `test_recommendation_distribution_and_support_are_pinned`, `test_enterprise_grid_edge_optimum_is_a_support_floor_not_a_modeled_peak`, `test_recommend_curves_are_non_decreasing_in_discount`). Wall time per test varies 2 to 3x between runs; outcomes do not.

## What improved since 2026-09-26

- 09-26 finding 1 (no down migrations): closed. Both migrations now have `.down.sql`, `neon/MIGRATIONS.md` documents up/down/up, and a pairing test exists (see finding 3 for the collection gap).
- 09-26 finding 2 (/ask untested): closed. `tests/test_rag.py` exists; /ask degrades cleanly with no provider and strips deal-level arrays.
- 09-26 findings 3 and 4 (mapping, docs): `tests/test_mapping.py` added; `pricing/docs.py` still has one indirect test file only.
- Mixed-currency upload now 422 with blockers instead of an unhandled exception (`api/main.py:330`).
- /recommend is rate limited (30/60s, customer-keyed) and thin CRM books refuse to quote a guardrail.
- Suite grew 279 to 456 Python, 11 to 33 web, with no flakes across two runs.
