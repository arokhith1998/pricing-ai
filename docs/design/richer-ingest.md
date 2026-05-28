# Phase 2.7 — Richer schema + robust ingestion

Status: approved to build, 2026-05-27. Confirmed with the founder.
Follows the buyer-funnel work (Phase 2.5).

## Goal

Two things that compound the value of the existing diagnostic:

1. **Hierarchy slicing.** Optional `business_unit`, `product_line`,
   `product_family`, `sku` columns. Whichever are present, the diagnostic
   automatically slices price realization / leakage / top-deals by them.
2. **Robust ingestion.** A prospect's CSV can have any column names and any
   reasonable file format. Map → review → run, never blind.

Explicitly **deferred** (each is its own design):
- Competitor-by-product-features intelligence (needs an external data
  partner / web pipeline; not a deal-data problem).
- Forecast accuracy (different product area — RevOps / pipeline analytics).
- Self-hosted LLM end-to-end (premature; current no-row-data rule is the
  durable privacy line).

## Schema additions

All **Optional** so existing customers / pure-SaaS prospects are unaffected.

| Field | Notes |
|---|---|
| `business_unit` | top-level group (e.g. "Cloud", "Data") |
| `product_line` | mid-level family of products |
| `product_family` | grouping within a line |
| `sku` | leaf product / SKU / part number |

The diagnostic exposes a `hierarchy_slices` payload with one entry per
dimension that has ≥2 distinct populated values. Web renders each as its own
"price realization by …" chart and feeds top-leak deals with hierarchy tags.

## Robust mapper (four layers, cheapest first)

```
prospect CSV/XLSX
  │
  1. Synonyms dictionary  (deterministic per field, case-insensitive)
  │
  2. Fuzzy match          (rapidfuzz token-set ratio on normalized header)
  │
  3. Local embeddings     (fastembed / BAAI-bge-small, ONNX, CPU)
  │
  4. Cloud LLM fallback   (headers only — never row data)
  │
mapping {our_field → their_header, confidence}
  │
  REVIEW UI (founder/prospect confirms or overrides)
  │
/diagnostic POST  ⟵ file + confirmed mapping
```

- Layers 1–3 are **fully local** (no external call).
- Layer 4 is only invoked for headers nothing matched with confidence; only
  header strings are sent.
- Sample-row type validation runs after mapping; surfaces "this column does
  not look like a date" before the engine sees it.

## File formats

`.csv` and `.xlsx` (via openpyxl on the API side).

## Privacy posture (tightened)

The buyer-funnel privacy page says aggregates and column-header names may
touch the cloud LLM. With Phase 2.7:

- Column header mapping is **local by default**; cloud is a fallback used
  only for unresolved headers. Update `/privacy` copy to reflect this.
- Row-level data: still **never leaves** (in-memory + immediate delete).

## What we are NOT doing in 2.7

- No fully self-hosted narrative LLM (cloud, aggregates only).
- No competitor enrichment.
- No forecast module.
- No mapping persistence across uploads (a "remembered mapping per prospect"
  is a nice future feature, but needs the lead/code identity tied to a
  mapping — defer).

## Open dependencies

- Add Python deps: `rapidfuzz`, `fastembed`, `openpyxl`. First fastembed
  call downloads the model (~30–100 MB, cached).
- Regenerate the synthetic dataset with a `business_unit` column so the
  sample demonstrates hierarchy slicing.
