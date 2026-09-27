# Code review: fix/agent-eval-findings vs origin/main

**Verdict: reject.** The governance, RAG and perimeter work is solid and tested, but the seams between the six worktrees leave one blocker: the metrics layer now refuses to manufacture a 0% reference, while top_leak_deals and the live CRM guidance still consume that 0.0 and turn it into "claw back every point" advice on a small book. Three of my eight earlier findings are closed only at the API layer and remain open through the product path (web never forwards the tenant header). Second-model pass not run: no OPENAI_API_KEY in this shell.

## Closed-findings checklist

1. Digest miscount: **closed**. pricing/governance.py:427-458, test_digest_counts_one_crm_override_not_the_approval_or_writeback.
2. Shared tenant bucket: **partial**. Length caps landed (api/routers/governance.py:43-47, api/routers/crm.py:184-185, tests). web/src/lib/gate.ts still returns "default" for every lead-gated visitor; visitor A's requested_by and justification are still readable by visitor B.
3. Uncaveated /recommend: **partial**. api/routers/model.py:116-123,163 adds caveat and method, tested. GuidanceClient.tsx never renders rec.caveat, method, or top_factors_at_recommended.
4. Em dashes: **mostly closed**. All three prompts forbid them, with tests; copilot literals cleaned. Still in user-facing strings: pricing/ingest.py:100,114,514 (load-report notes), pricing/diagnostic.py:354, pricing/matching.py:407 (extraction prompt).
5. Rate limiter key: **partial**. api/main.py:188-214 keys on X-Pricekeel-Customer, XFF gated by PRICEKEEL_TRUST_PROXY, tested. But web/src/lib/api.ts:481-494 forwards the header only on /exceptions and /digest; /ask, /copilot, /docs, /matching, /recommend send none, so through the product every request still lands in one ip: bucket.
6. Doc store tenant scope: **partial**. api/routers/rag.py keys on (customer_ref, session_id), tested. web/src/app/api/docs/route.ts and ask/route.ts do not forward the header, so every product upload lands under ("default", sid) and any lead visitor holding the sid reads it via /api/ask. Exposure unchanged in practice.
7. /ask deal-level leakage: **closed**. rag._strip_deal_level, three tests, docstrings corrected.
8. Repeated bootstrap: **worse in metrics, better in crm**. crm.analyze_records memoizes (tested). metrics.py now calls reference_discount 153 times per diagnostic.run on the demo book (probe), because hierarchy_slice_reference, defended_vs_investigate, trend_by_quarter and policy_simulations call _per_deal_reference without bu/product-line refs, rebuilding both tables per call. Fix: compute the three tables once in diagnostic.analyze and thread them through.

## New findings

**BLOCKER. Manufactured 0% reference survives where a rep sees it.** metrics.top_leak_deals (pricing/metrics.py:848-856) and crm._reference_for_segment (pricing/crm.py:119-135) ignore ref["sufficient"]. Probe on a 42-deal book (MIN_CLOSED_DEALS is 30, so reachable): leakage says "insufficient data, $0"; top_leak_deals lists 15 deals with $312k excess; guidance_for_open_deal returns reference 0.0, band "None", recommends 0% discount, price_to_retain $15k; crm_workflow then sets guardrail_pct 0 and outside_guardrail True for any request. Fix: return an empty frame with a basis column from top_leak_deals, and raise CRMDataError from guidance_for_open_deal (crm_workflow already maps it to 422); add both to test_metrics and test_crm.

**MAJOR. /recommend uplift is measured at the wrong point.** pricing/model.py:432-441: with the clipped grid, cur_i snaps to the nearest grid edge, so expected_acv_at_current is the EV at that edge. Probe: 28 of 400 won demo deals sit outside their cohort grid; OPP-00007 (Enterprise, 11.2% actual) gets grid 14-32%, recommended 14%, uplift $0, i.e. more discount at a reported zero cost. Fix: np.union1d(grid, [current]) or score current separately. Also pricing/governance.py:354 still calls recommend_discount without cohort, so /exceptions and /recommend can disagree on the same deal.

**MAJOR. Mixed-currency block keys on symbols only.** pricing/ingest.py: mixed = len(report.currencies) > 1 comes from the symbol scan; the currency-column branch runs after the block. Probe: 40 rows with currency USD/EUR and no symbols: not blocked, totals summed. A Salesforce CurrencyIsoCode export is exactly this shape. Fix: derive mixed from the union of symbol codes and the upper-cased currency column before the check; test it.

**MAJOR. evidence_version does not fingerprint the book.** api/routers/crm.py:92-103 hashes len(records), a sync timestamp that is always "none" today, threshold, method, SHA. Probe: two different two-deal books hash identically. Fix: add a sha256 of canonical JSON of records sorted by opportunity_id. Determinism is otherwise fine (env SHA wins; git subprocess only in dev).

**MAJOR. Lead capture regression in the index migration.** neon/migrations/2026-09-26-tenant-scoped-indexes.sql adds a unique index on leads(lower(email)). email was never unique, saveLead (web/src/lib/store.ts:57-67) has no ON CONFLICT and no leadExists pre-check. The migration fails if prod holds a repeat email, and afterwards a returning visitor re-submitting the form gets the retry message and no cookie. Fix: make it a plain index, or dedupe and add ON CONFLICT DO NOTHING first.

**MINOR.** crm_reconcile inserts up to 5000 rows one at a time; a mid-loop prod fallback 503s after partial writes (api/routers/crm.py:404-419). CRMWritebackReq.actor and task_id lack max_length.

## Fail-closed path and the demo tier

Safe. _insert_or_fail_closed is wired only into /crm/workflow, /crm/reconcile, /crm/writeback; /exceptions and copilot keep the memory fallback with 200. Demo pages call /exceptions and /recommend, never /crm/*. Access-code Salesforce customers will 503 when Neon is down, which is the intent.

VERDICT: reject. Fix first: propagate ref["sufficient"] into top_leak_deals and crm guidance so a thin book never becomes a 0% guardrail on a live override.
