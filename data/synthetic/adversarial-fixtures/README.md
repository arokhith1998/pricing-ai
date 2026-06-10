# Adversarial fixtures — round 2 ingestion stress test (2026-06-10)

Round 1 (`data/synthetic/format-fixtures/`) proved header/format variety works.
This round attacks with **silent-corruption traps** — cases that produce wrong
numbers without raising errors. Same 300 canonical deals underneath. Each
fixture has its own pass condition, including "must fail loudly."

    PYTHONPATH=. python tools/make_adversarial_fixtures.py
    PYTHONPATH=. python tools/check_adversarial_fixtures.py

## Results (2026-06-10) — 4/9 pass

```
uk_dates         PASS  all 300 dates correct (dayfirst detected)
open_pipeline    FAIL  rows=340 (want 300), win_rate=0.474 (want 0.537)
credits_zero     PASS  inf discounts=0, negative parsed ok=True
dupe_opps        FAIL  total drift 3.6% — duplicates double-counted
cp1252_names     FAIL  crashed: UnicodeDecodeError
space_thousands  PASS  total drift 0.0%
multisheet       FAIL  failed: SchemaError
header_only.csv  FAIL  returned 0 rows from a non-dataset!
garbage.csv      PASS  raised SchemaError
```

## Fix list (priority order — silent corruption first)

1. **open_pipeline (SILENT, CRITICAL).** A CRM export containing open deals
   (Negotiation, Proposal Sent, …) ingests as 340 rows and reports a win rate
   of 0.474 instead of 0.537 — *wrong number, zero errors*. Rows whose stage
   doesn't resolve through OUTCOME_ALIASES must be **excluded and counted in a
   load report** ("excluded 40 rows with non-closed stages: …"), never retained.
2. **dupe_opps (SILENT, CRITICAL).** Exact re-export duplicates double-count
   booked ACV by 3.6%. Deduplicate on `opportunity_id` (exact-row dupes drop
   silently into the load report; same-ID-different-values rows should be
   flagged as a data-quality error).
3. **header_only (SILENT).** A header-only file returns an empty DataFrame;
   downstream metrics become NaN dashboards. `validate` should require ≥1 data
   row (and probably ≥30 closed deals for a meaningful diagnostic — make the
   minimum explicit and message it).
4. **cp1252_names (CRASH).** Windows exports are routinely cp1252. Decode
   cascade: utf-8-sig → cp1252 → latin-1, and record which was used in the
   load report. Never `errors="replace"` silently — mojibake breaks identity
   resolution.
5. **multisheet (LOUD but wrong).** Excel workbooks with a summary sheet first
   fail outright. Try each sheet, score by share of required fields the header
   mapper resolves, pick the best; note the chosen sheet in the load report.

## The pattern behind all five

Every fix above wants the same artifact: a **load report** returned alongside
the DataFrame (rows read / excluded and why / dupes dropped / encoding /
sheet chosen / date format inferred). That report is also exactly what the
customer-facing diagnostic should print first — "here is what we read from
your file" — which is the explainability posture the whole product claims.
Build `ingest()` to return `(df, LoadReport)` (or add `ingest_verbose()`),
surface it in the Streamlit dashboard, and extend
`tests/test_format_fixtures.py` with these 9 cases once green.

## Status — RESOLVED (2026-06-10)

- [x] Fixes 1–5 implemented via the LoadReport design (`pricing.ingest.ingest_verbose`
      returns `(df, LoadReport)`; `ingest()` stays a back-compat df-only wrapper).
- [x] `tools/check_adversarial_fixtures.py` reports 9/9.
- [x] Cases promoted into `tests/test_adversarial_fixtures.py` (CI-gating), each
      asserting both the DataFrame and the LoadReport.
- [x] LoadReport surfaced in the Streamlit dashboard ("What we read from your
      file" on the Data and identity page).

Bonus catch: dedup exposed a latent mis-mapping the round-1 total had hidden —
HubSpot's `Record ID` was unmapped while `Deal owner` fuzzy-grabbed
`opportunity_id`. Fixed with explicit synonyms (`record id` → opportunity_id,
`deal owner` → rep_id).
