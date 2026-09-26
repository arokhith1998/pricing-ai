# Pricekeel backend/engine evaluation (read-only)

## Verdict

The deterministic core is disciplined: explainability is enforced as a coding
habit, not a slogan (LoadReport disclosure, method labels on every verdict,
CRM proxy vs margin boundary respected: grep for "margin" across
metrics/diagnostic/governance/crm/ingest returns nothing). The API perimeter
is genuinely hardened for the threats it names: auth, upload caps, per-IP
rate limiting, CORS fail-closed, SSRF-proof outbound fetch. Numeric metric
definitions (price realization, discount leakage, win rate by band) are
correct and match the stated methodology. The two real problems are: PK-16 is
confirmed and reproducible, the hierarchy dimensions have no reference table
at all, not even a fallback-labeled one; and the usage/hybrid commit-ramp-
overage requirement in CLAUDE.md is not met anywhere in the owned engine, the
schema carries the fields but nothing reads them.

## Top 6 findings

1. **PK-16 confirmed, worse than described (Medium-High).** `metrics.py:451-462`
   `_per_deal_reference` maps every deal's excess-reference threshold by
   `segment` only. There is no `business_unit`/`product_line` equivalent of
   `segment_reference_table` (`metrics.py:345-393`). `hierarchy_slices` in
   `diagnostic.py:58-61` calls only `realization_by`, which has no reference
   or excess column at all. Verified live: global reference is 5%, Enterprise
   segment's own is 10%, but a BU or product line with a similarly divergent
   curve is silently scored against segment (or global) reference in
   `leakage()`, `top_leak_deals()`, and `policy_simulations()`. Fix: a
   `business_unit_reference_table` / `product_line_reference_table` mirroring
   `segment_reference_table`, and route `_per_deal_reference` through the
   deal's own BU when it earns one, same sufficiency bar (100 deals, 3 bands).

2. **Commit/ramp/overage fields are dead weight (High).** `schema.py:121-140`
   defines `committed_acv`, `overage_rate`, `ramp_year_1_acv`,
   `ramp_year_2_acv`, `renewal_uplift`. Grep across `metrics.py`,
   `diagnostic.py`, `crm.py`, `governance.py` shows zero usage. Every
   reference discount, leakage lens, and guardrail speaks discount % only,
   exactly the ICP mismatch CLAUDE.md flags as a known panel gap. For a
   usage/hybrid-first product this is a positioning liability, not a nice-to-have.

3. **JSON body size is unguarded on `/crm/*` (Medium, perimeter gap).**
   `MAX_UPLOAD_BYTES` is enforced only for `UPLOAD_PATHS =
   {"/map-headers","/diagnostic","/docs/upload"}` (`api/main.py:84,189-201`).
   `CRMAnalyzeReq.records: list[dict]` (`api/main.py:908`) and
   `CRMReconcileReq.outcomes` (`api/main.py:1125`) have no perimeter-level
   cap; `MAX_CRM_RECORDS = 10_000` (`crm.py:19`) only fires after Starlette
   and pydantic have already deserialized the full body into memory. A large
   JSON payload is fully parsed before rejection. Add the same
   content-length gate to the CRM paths.

4. **`/recommend` is the one uncapped model-cost endpoint (Low-Medium).**
   `RATE_LIMITS` (`api/main.py:95-110`) covers `/exceptions` (same EV sweep,
   30/60s) but omits `/recommend` (`api/main.py:1365`) entirely, so the
   otherwise-consistent "rate-limit anything CPU/model-adjacent" rule has one
   hole.

5. **`defended_vs_investigate` uses the global reference while `leakage`'s
   headline is segment-aware (Medium, internal consistency).**
   `metrics.py:546` calls `reference_discount(df)` (global) inside
   `defended_vs_investigate`, while `leakage()` (`metrics.py:492-515`) headlines
   the segment-aware excess. Two different bases answer what looks like the
   same question on the same readout; a customer reconciling the "Leakage"
   section against the "defended vs investigate" split will not get numbers
   that tie out, and there is no basis disclosure on this function the way
   there is on `segment_reference_table`.

6. **Rate limiter and doc/session stores are single-process state (Low, scaling).**
   `_RATE_BUCKETS`, `_DOC_STORE`, and `_ENGINE`/`_DIGEST_BOOK` caches
   (`api/main.py:112,551,458,869`) are plain in-process dicts. On >1 Render
   instance or worker, the effective rate limit becomes `limit × workers`,
   silently. Docs module already discloses this for `_DOC_STORE` ("dev
   fallback; production should move to Neon pgvector"); the rate limiter has
   no equivalent disclosure and is the security-relevant one.

## Three genuinely good things

- `pricing/_safe_fetch.py` is rare-quality SSRF defense: resolve-then-pin
  against DNS rebinding, per-hop redirect re-validation, fail-closed when no
  safe IP is pinnable, byte cap during streaming. This is staff-level work.
- `pricing/ingest.py`'s `LoadReport` (`ingest.py:41-111`) makes every silent
  data-corruption trap (duplicate rows, mixed currency, ambiguous
  day/month dates, open deals leaking into win rate) a visible disclosure
  line instead of a wrong number. This is the explainability posture applied
  correctly to the boundary that actually breaks trust first.
- `pricing/governance.py` labels every verdict's `method`
  (`modeled_ev_curve` vs `band_guardrail`, e.g. `governance.py:406`,
  `crm.py:176`) so the live-Salesforce path is never passed off as the
  stronger demo engine, and the `persisted` flag on every write
  (`governance.py:118-162`) never claims durability the store did not
  actually achieve.

## Fix next week

Close PK-16 properly: build `business_unit_reference_table` and
`product_line_reference_table` mirroring `segment_reference_table`'s
sufficiency bar and basis disclosure, then route `top_leak_deals`,
`leakage`, and `policy_simulations` through the deal's own hierarchy
reference when it earns one. It is the same pattern already proven for
segments, it is scoped to `pricing/metrics.py`, and it removes the one
concrete, customer-facing methodology gap on the open backlog.
