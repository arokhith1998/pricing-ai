# Format fixtures — ingestion stress test (2026-06-10)

Six exports of the **same 300 synthetic deals** (`data/synthetic/format-base.csv`),
re-serialized the way real companies export them. A correct pipeline produces
identical metrics from every file. Regenerate / re-check:

    PYTHONPATH=. python tools/make_format_fixtures.py
    PYTHONPATH=. python tools/check_format_fixtures.py

| Fixture | Mimics | Tricks |
|---|---|---|
| salesforce_export.csv | Salesforce report export | Title Case headers, "Closed Won", MM/DD/YYYY, "$1,234.56", CRLF |
| hubspot_export.csv | HubSpot deals export | "Record ID"/"Deal Stage", "closedwon", ISO datetimes |
| eu_export.csv | EU ERP/CRM export | semicolon delimiter, DD.MM.YYYY, decimal commas "1.234,56", ja/nein |
| warehouse_export.csv | dbt/warehouse dump | UPPER_SNAKE abbreviations (OPP_ID, ACCT_NAME), 1/0 booleans |
| finance_export.xlsx | Finance's Excel | title+blank rows above header, currency strings, TOTAL row, mid-table blanks |
| messy_export.csv | hand-maintained CRM | BOM, padded/mixed-case headers, **no account_id**, mutated names, blank rows |

## Status: RESOLVED (2026-06-10)

Fix-list items 1–6 are done. All six fixtures now ingest through `pricing.ingest.ingest()`
and reproduce the canonical booked-ACV total within 0.5%, verified by
`tests/test_format_fixtures.py` (which replaces the old `tools/check_format_fixtures.py`).
The results table below is the **pre-fix baseline**, kept as the record of what broke.

## Results (2026-06-10, layers 1–2 of the mapper only — no embeddings/LLM) — PRE-FIX BASELINE

```
fixture                raw_ingest             headers                      values  total
eu_export.csv          FAIL (ParserError)     FAIL missing=[booked_acv]
finance_export.xlsx    FAIL (UnicodeDecode)   FAIL missing=[segment, booked_acv]
hubspot_export.csv     FAIL (SchemaError)     FAIL missing=[booked_acv]
messy_export.csv       FAIL (SchemaError)     FAIL missing=[product_tier]
salesforce_export.csv  FAIL (SchemaError)     PASS                         PASS    PASS
warehouse_export.csv   FAIL (SchemaError)     FAIL missing=[account_name, product_tier]
```

## Findings → fix list (for the coding agent)

1. **`ingest()` never calls `mapping.map_headers()`** — the 4-layer mapper exists
   but is unwired, so raw ingest fails on 6/6 real-world formats. Wire it:
   load → strip/map headers → validate → coerce.
2. **`load_csv` can't read** semicolon-delimited CSVs or .xlsx; no delimiter
   sniffing, no header-row detection, no BOM handling. `check_format_fixtures.read_any`
   shows the tolerant pattern.
3. **Value normalization is missing entirely:**
   - outcome: only `closed_won|closed_lost` accepted — "Closed Won", "closedwon",
     "Won", "W", "WON" all fail. Need an alias map (see OUTCOME_ALIASES in checker).
   - money: `pd.to_numeric` NaNs out "$96,000.00" and EU "96.000,00" — silent
     total corruption, the worst failure class. Use a tolerant money parser.
   - dates: MM/DD/YYYY vs DD.MM.YYYY ambiguity needs explicit per-file format
     detection, not pandas defaults (silently swaps day/month below the 13th).
4. **Synonym gaps in `mapping.py`:** `booked_acv` misses "amount", "deal amount",
   "net price", "contract value", "net acv"; `account_name` misses "acct name";
   abbreviations (TIER, SEG, QTY) unmatched at fuzzy threshold 88.
5. **Synonym collision:** "tier" is a *segment* synonym, so a `tier` column
   (meaning product_tier) maps to segment. When both columns exist, product_tier
   is lost. Mapping must be one-to-one with conflict resolution, not first-match.
6. After fixes, convert `tools/check_format_fixtures.py` into
   `tests/test_format_fixtures.py`: every fixture must ingest and reproduce the
   canonical booked-ACV total within 0.5%.

Layers 3–4 of the mapper (embeddings/LLM) may catch some header gaps, but
deterministic synonyms are free, local, and explainable — grow them first.
