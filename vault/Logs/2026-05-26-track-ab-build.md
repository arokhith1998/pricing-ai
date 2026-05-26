---
title: Track A + B build — Phase 1 & 2 shipped
created: 2026-05-26
updated: 2026-05-26
tags: [log, build, engineering, gtm, ml, track-a, track-b]
status: active
---

# Track A + B build (2026-05-26)

First build session. Stood up the product from an empty repo. See
[[2026-05-26-kickoff-decisions]].

## Shipped
- **Track A — Phase 1 diagnostic** (`pricing/`): canonical deal schema →
  synthetic generator → ingest + identity resolution → leakage metrics →
  Streamlit dashboard. CLI: `python -m pricing.diagnostic`.
- **Track A — Phase 2 model** (`pricing/model.py`): LightGBM win-probability on
  quote-time features, native SHAP explanations, expected-ACV discount guidance.
- **Track B — GTM** (`gtm/`): design-partner targets, outreach sequence, and a
  data-request spec generated from the same schema as the synthetic data.

## Key decisions (the "why")
- **Schema is the single contract** shared by data, metrics, and the GTM data
  request → a real partner's CSV is drop-in, not a redesign.
- **Streamlit over Next.js** for the week-1 demo — local-first, fast. Next.js
  waits for a customer-facing product.
- **Leakage = three lenses** (gross discount, off-policy, excess-vs-reference).
  The excess lens is **correlational, not causal** — an investigate-list, not a
  refund figure. Validate methodology with an advisor before showing a customer.
  Grounded in [[nagle-strategy-and-tactics-of-pricing]] (EVC / reference price)
  and [[simon-kucher-discount-governance]].
- **Model trains on quote-time features only** (no outcome leakage; enforced by
  a test). Synthetic AUC ~0.64 with strong calibration — discrimination is
  capped by deliberate irreducible noise; calibration + explainability matter
  more for guidance ("explainability > accuracy"). See
  [[campbell-willingness-to-pay]] for the WTP/value-metric basis.

## Repo state
- Branch `main`: Phase 1 + Phase 2 (merged) + deploy scaffolding (Dockerfile).
- 15 tests passing. Pushed to a private GitHub repo under `arokhith1998`.
- Synthetic data only; real partner data routes to gitignored `data/private/`.

## Open threads
- No design partner yet — sourcing remains the critical path
  ([[ideal-first-design-partner]]).
- `bertini-koenigsberg-ends-game` framework note still a stub.
- Phase 3 (live integration, Snowflake) deferred until a signed pilot.

## Related
[[2026-05-26-kickoff-decisions]] · [[pricing-frameworks-index]] ·
[[ideal-first-design-partner]] · [[track-a-b-vocabulary]]
