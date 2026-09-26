# Pricekeel QA gate evaluation, 2026-09-26

## Verdict: PASS, with two findings to open follow-up tasks for

Python suite: 279 passed, 0 failed, 1 warning (harmless huggingface symlink notice), 49.46s,
via `C:\Pricing-AI\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`. Web: `npx eslint`
clean (no output, exit 0), `npx tsc --noEmit` clean once a stale gitignored `.next/` build
artifact was removed (see finding 4), `npm test` 4 files / 11 passed, `npm run build` succeeded
with no secrets present (only `.env.local`, gitignored, holding a Vercel OIDC token and access
codes neither of which the build required). CI verdict: main branch latest `ci` run
**35029845998**, success, both jobs green (Python tests 1m14s, Web lint/types/tests/build
1m21s). Current branch `feat/agent-engineering-org` latest push run **35033658978**, also
success. Nothing here is agent-reported; I ran every command myself.

## Top 6 findings

1. **[High] No down migrations anywhere.** `neon/migrations/` holds exactly one file,
   `2026-08-01-salesforce-crm-workflow.sql`, and it is `up` only (create table/index, no drop).
   There is no `.down.sql`, no rollback script, no reference to reverting a migration in
   `neon/CUTOVER.md`. If this migration ships something wrong there is no tested path back to
   the prior schema state, and no test exercises the intermediate state between migration and
   deploy. Recommendation: add a paired down script per migration and a test/runbook step that
   applies up, verifies, applies down, verifies clean, before merging the next migration.

2. **[High] `/ask` (the RAG endpoint) has zero test coverage.** `pricing/rag.py:1-20` synthesizes
   answers from three sources (analysis JSON, uploaded doc chunks, optional public web) and
   claims every output cites `[A]`/`[D#]`/`[W#]` and never sends row-level data. `api/main.py:680`
   wires it to `POST /ask`. Grep across `tests/*.py` for the literal `"/ask"` route returns
   nothing except a rate-limit comment (`tests/test_api_perimeter.py:243`) and the rate-limit
   table entry (`api/main.py:96`). No test checks the citation contract, the tenant boundary on
   retrieved doc chunks, or that row-level data actually stays out of the prompt. This is exactly
   the class of silent, high-trust failure this repo has already shipped twice.

3. **[Medium] `pricing/mapping.py` has no direct unit test.** The four-layer header-mapping
   cascade (synonyms, fuzzy, local embeddings, cloud LLM fallback, `pricing/mapping.py:1-14`) is
   only reachable indirectly through `/map-headers` and `/map-columns` perimeter tests, which
   check auth/rate-limit, not mapping correctness. No test asserts a messy header (e.g. "Deal #",
   "Opp ID") actually resolves to the right canonical field, or that the LLM fallback layer is
   truly opt-in and never receives row data as the docstring promises.

4. **[Medium] `pricing/docs.py` has no direct unit test.** The PDF/DOCX/MD/TXT chunker feeding
   `/docs/upload` is only exercised at the perimeter (size caps in
   `tests/test_api_perimeter.py:178,192`), not for correctness: malformed PDF, empty document,
   or a doc with no extractable text are all untested paths into the RAG pipeline in finding 2.

5. **[Low, environment hazard] Stale `.next/dev/types` broke `tsc --noEmit` locally**
   (`web/.next/dev/types/routes.d.ts:114`, `validator.ts:443`, both `TS1109`/`TS1128`, truncated
   mid-token). `.next/` is gitignored (`web/.gitignore:17`) and CI always runs from a clean
   checkout, so this is not a repo bug, but it matches the "torn-write corruption" pattern
   already flagged in project memory. Deleting `.next/` and re-running fixed it. Worth a
   `predev`/`pretest` hygiene note so a contributor doesn't chase a phantom type error.

6. **[Low] `funnel-tracker.csv` real-vs-example split not present in this repo.** Searched
   `tests/*.py` and `pricing/*.py` for `funnel-tracker`/`funnel_tracker`, zero hits. If this is
   meant to exist per the QA brief, it either lives elsewhere or has not shipped yet; flagging so
   it isn't silently assumed covered.

## Three genuinely good things

- `tests/test_api_perimeter.py` is a real security regression suite (auth, upload size, sliding
  rate limits, load_report) written after a named CTO review, not an afterthought.
- `.github/workflows/ci.yml` has a self-aware comment: it exists because a Salesforce OAuth
  tamper test failed "roughly one run in sixteen" locally before CI enforced it on every push,
  and the build step deliberately runs with no secrets so a future secret requirement is treated
  as a regression, not a config gap.
- `tests/test_agentctl.py` (46 tests) treats the multi-agent task state machine itself as
  trust-critical, same tier as `pricing/metrics.py`, with explicit known-answer tests for the
  ownership/merge gate.

## One thing to do next week

Write `tests/test_rag.py`: cover the citation contract, an injected/malicious doc chunk, a
missing-analysis-JSON case, and a cross-tenant doc-chunk leak attempt against `POST /ask`. That
closes the largest untested trust-critical surface found in this pass.
