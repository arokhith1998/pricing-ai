# Pricing Intelligence Platform

System of record for pricing decisions for B2B SaaS companies on usage-based /
hybrid models. **Wedge:** a free retrospective *discount-leakage diagnostic*
built from a CSV of a prospect's closed deals.

> Phase 1 (this repo today): CSV-only diagnostic on synthetic data. No
> warehouse, no ML, no customer data. See
> `vault/Decisions/2026-05-26-kickoff-decisions.md` for the 90-day plan.

## What it does

Given one row per closed opportunity (won + lost), it computes:

- **Price realization** (booked ÷ list) overall and by segment.
- **Win rate by discount band** — the curve that reveals whether discounting
  actually buys wins.
- **Leakage**, through three lenses (weakest → strongest claim):
  1. *Gross discount $* — total list-to-booked giveback (descriptive).
  2. *Off-policy $* — discount above the policy threshold (governance).
  3. *Excess-vs-reference $* — discount above the level where win rate stops
     improving. **Correlational, not causal** — a prioritized list of deals to
     investigate, not a refund figure.
- **Quarter-end effect**, **governance gaps** (off-policy with no approver),
  and a **top-deals-to-investigate** list.

Identity resolution collapses messy account names ("ACME, Inc." / "acme") and
missing IDs into resolved accounts.

## Quickstart

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "."          # so `pricing` is importable

# 1. generate a synthetic demo dataset
python -m pricing.generate -n 2000 --seed 7 -o data/synthetic/deals.csv

# 2. run the diagnostic in the terminal
python -m pricing.diagnostic data/synthetic/deals.csv

# 3. train the win-probability model + see discount guidance (Phase 2)
python -m pricing.model data/synthetic/deals.csv

# 4. or open the dashboard (diagnostic + guidance)
streamlit run app/dashboard.py
```

Run the tests (the leakage math is unit-tested — it's the trust-critical part):

```powershell
$env:PYTHONPATH = "."; python -m pytest -q
```

## Layout

```
pricing/        core package
  schema.py       canonical deal schema — the single source of truth
  generate.py     synthetic deal generator (realistic, with a real leak baked in)
  ingest.py       load + validate + identity resolution + derived fields
  metrics.py      leakage, price realization, win-rate-by-band (unit-tested)
  diagnostic.py   orchestration + CLI report
  model.py        Phase 2: win-probability + native SHAP + discount guidance
app/
  dashboard.py    Streamlit home (overview + flow/architecture diagram)
  _app_lib.py     shared brand kit + cached diagnostic/model loaders
  pages/          Diagnostic · Win model & guidance · Data & identity · Methodology
api/            FastAPI wrapper over the engine (serves JSON to the web UI)
web/            Next.js buyer-facing UI (Pricekeel brand), consumes api/
brand/          Pricekeel brand kit — logo SVGs, palette, brand guide
gtm/            Track B — design-partner sourcing, outreach, data-request spec
data/
  synthetic/      generated demo data (committed)
  private/        real customer data (gitignored — NEVER committed)
tests/          known-answer tests for the metrics + identity layer
```

## Onboarding a real partner

The synthetic data and the GTM **data-request** (`gtm/data-request.md`) are
generated from the same `pricing/schema.py`, so a partner's CSV is a
column-mapping exercise, not a schema redesign. Their data goes in
`data/private/` (gitignored) and is handled under the NDA at
`docs/legal/one-page-mutual-nda-data-addendum.md`.

## Web UI (Next.js)

The buyer-facing UI is a Next.js app in `web/` that reads from the FastAPI
service in `api/`. Run both:

```powershell
# 1. the API (serves the engine as JSON)
$env:PYTHONPATH = "."
uvicorn api.main:app --port 8000

# 2. the web UI (in another terminal), pointed at the API
cd web
$env:PRICEKEEL_API = "http://127.0.0.1:8000"
npm run dev        # open http://localhost:3000
```

Streamlit (`app/`) stays as the internal, fast-iteration tool. The Next.js app
is the polished, plain-language surface for customers. Both consume the same
`pricing/` engine, so they never drift. See `docs/design/nextjs-ui.md`.

## Deploy

The dashboard is a containerized Streamlit app.

```bash
docker build -t pricing-ai .
docker run -p 8501:8501 pricing-ai     # open http://localhost:8501
```

Works on any container host (Fly.io, Render, Google Cloud Run). For a
zero-infra demo, **Streamlit Community Cloud** runs straight from this repo —
point it at `app/dashboard.py` with `requirements.txt`.

> The container ships only the **synthetic** dataset. This is an internal /
> demo tool: put it behind SSO before exposing it, and never bake real
> `data/private/` data into an image or a public deployment.

## Deliberate scope choices

- **Streamlit, not Next.js** for the week-1 demo — local-first, fast. A
  customer-facing UI comes later.
- **Phase 2 (this branch)** — win-probability via LightGBM, explained with
  LightGBM's *native* SHAP contributions (no extra `shap` dependency), plus
  expected-ACV discount guidance. Trained only on quote-time features (no
  outcome leakage). Synthetic-data AUC ~0.64 with strong calibration — discrimination
  is capped by deliberate irreducible noise; calibration + explainability are
  what matter for guidance. Warehouse (Snowflake/Fivetran) still deferred to Phase 3.
- **CSV, not Snowflake** — warehouse + Fivetran deferred to Phase 3.
