# Code review, day 2: tree 00bd935 (main cf37f27 + agent-org docs)

Read-only. Suite not run (QA owns it); findings were reproduced with throwaway Python. Second-model pass not run (no key in this shell).

## Verdict

PR #69 closed all thirteen prior findings for real, with tests that assert behavior. It also introduced one blocker: the "segment-aware" headline the sample page calls lower and more defensible is now higher than the global lens it labels as overstating. VERDICT: reject.

## Closure checklist (eight original)

1. Digest miscount: closed. governance.py:437-456 filters to override_requested and reads outside_guardrail; known-answer test test_governance.py:499.
2. Shared tenant bucket: closed. gate.ts:68-82 mints a signed demo:<uuid>; every proxy forwards it (ask:24, docs:22, copilot:16, matching:13, recommend:21, exceptions:61,90, diagnostic:28); caps at governance.py:47-48, crm.py:222-223,515-518.
3. Uncaveated /recommend: closed. model.py router 119-124,168; GuidanceClient.tsx:387-390 renders it, 432-438 renders top_factors_at_recommended.
4. Em dashes: closed for generated and user-facing strings. Python scan finds them only in comments and docstrings (metrics.py:1, copilot.py:1, diagnostic.py:1); ingest.py, matching.py, governance.py clean.
5. Rate-limit key: closed. main.py:189-214 keys on tenant, XFF gated by PRICEKEEL_TRUST_PROXY; test_api_perimeter.py:249.
6. Doc store tenant scope: closed. rag.py:42-65 keys on (customer_ref, session_id), docs and ask proxies forward the header.
7. /ask deal-level leakage: closed. rag.py:73-118 _strip_deal_level, called at rag.py:294.
8. Repeated bootstrap: closed. diagnostic.py:38-43 threads four tables; probe counts 19 reference_discount calls per run, down from 153.

## Round-1 findings (five)

Manufactured 0% reference: closed (metrics.py:960-962, crm.py:135-141,196-205; test_metrics.py:188, test_crm.py:181-203). Uplift at wrong grid point: closed (model.py:536-543,613; test_model.py:531). Mixed-currency ISO column: closed (ingest.py:758-761; test_ingest.py:210), with a new edge below. evidence_version fingerprint: closed (crm.py router 77-92; test_crm.py:628). Unique lead-email index: closed (migration is a plain index, lines 17-29).

## New findings

BLOCKER. Headline excess now exceeds the lens labeled "overstates by design". pricing/metrics.py:575-587 applies BU and product-line references over the segment one. On the demo book BU "Data" and three product lines earned a 0% reference (band floor of the 0-5% band), so 56 of 180 Enterprise won deals are measured at 0% instead of their segment's 10%. Reproduced: headline excess_vs_segment_reference_won is $12.48M under this precedence, $8.95M segment-only, $11.22M global. sample/page.tsx:150 and :296-305 show the $12.48M as "past each segment's own reference win point" beside "Global reference: $11.2M (overstates by design)". The bundled fallback (sample-fallback.json) still holds $8.95M, so the public headline changes by $3.5M depending on whether the API answered. Fix: in _per_deal_reference apply segment own first, then BU, then product line, then global (segment is where the 2026-06-10 dry run showed the curve differs); regenerate sample-fallback.json; add a known-answer test pinning the demo headline.

MAJOR. The emailed digest is now for a tenant nobody writes to. api/digest/send/route.ts:38 calls getDigest() with the "default" tenant (api.ts:522). After the per-visitor tenant fix, every web write lands under demo:<uuid> or an access code, so the cron email will report zero activity forever. Fix: iterate tenants with activity in the window server-side (a GET /digest/all behind the cron key), or send per access-code customer.

MAJOR. Explicit currency column with null cells blocks the book. ingest.py:759-761 does astype(str) on the column, so None becomes "NONE" and NaN becomes "NAN", and nunique()>1 raises "Mixed currencies: NONE, USD". Reproduced via ingest_frame_verbose; the CRM path reaches it whenever a JSON caller sends currency_iso: null (crm._currency_guard passes it, then ingest blocks). The web adapter sends "" (salesforce-adapter.ts:70-73) so today's live path is safe. Fix: treat "", "nan", "none", "null" as blank before the mask; test it.

MINOR. /copilot/log has no caps: copilot.py router 64-69, note, session_id, accepted, rejected are unbounded lead-gated writes into Neon, the same class fixed on /exceptions. Add Field max_length and list caps.

MINOR. crm.py:289-290 recomputes global_ref and segment_table that analyze() at :282 already produced (analysis["reference_discount"], analysis["leakage"]["segment_references"]).

NIT. Stale comments: api.ts:452-454 still says "default" for demo visitors; the index migration (line 14-15) says /digest reads across tenants, it does not.

## Genuinely good

The insufficient-data state propagates end to end with tests (test_metrics.py:188). _insert_or_fail_closed plus the reconcile pre-probe (crm.py router 407-458) is the right shape.

## Fix next week

Reorder _per_deal_reference so the segment reference wins, pin the demo headline with a known-answer test, regenerate the fallback. Until then the sample page's strongest number exceeds the one the engine says overstates.

VERDICT: reject. Fix first: the BU-over-segment precedence in pricing/metrics.py:575-587.
