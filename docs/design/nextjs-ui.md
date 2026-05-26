# Pricekeel Web UI (Next.js) — design doc

Status: draft, 2026-05-26. Owner: founding engineer.

## Why

The Streamlit demo proves the engine but is the wrong surface for a buyer. It
reads as a data tool: too technical, full of abbreviations (ACV, AUC, Brier,
SHAP), raw field names with underscores (booked_acv, discount_pct), and limited
visual polish. Streamlit has a ceiling here. The people we sell to (a Head of
Pricing and a CFO) want plain language, money first, and a calm, credible look.

This doc scopes a customer facing web UI in Next.js that is clear to a
non technical buyer, polished and lightly animated, and responsive. The Python
analytics engine does not change; the new UI consumes it through an API.

## Design rules (from founder feedback, non negotiable)

1. Plain language first. No unexplained abbreviations. Spell terms out, keep the
   short form in parentheses only when useful (for example "annual contract
   value"). Put model statistics behind an "Advanced" disclosure.
2. No em dashes in any UI copy. Use commas, periods, colons, or parentheses.
3. No raw field names. Every label is human readable. Never show snake_case
   (for example show "Booked value (annual)", not booked_acv). One central
   label map drives this (appendix A).
4. Lead with dollars and the decision, not the method. A CFO should grasp the
   headline in five seconds. Technical detail is opt in.
5. On brand. Use the Pricekeel kit: Keel Navy, Waterline Teal, Leak Coral,
   Inter, the keel logo. Calm, precise, confident. No hype.

## Audience and tone

Primary viewer is a revenue or finance leader, not a data scientist. Replace
jargon as in appendix B (for example "win probability" not "P(win)", "top
factors" not "SHAP values", "expected value" spelled out).

## Stack

- Next.js (App Router) with TypeScript and Tailwind CSS.
- Component library: shadcn/ui (Radix based, accessible, easy to theme to the
  brand palette).
- Charts: Tremor (dashboard friendly, fast, themeable) or Recharts. Lean Tremor.
- Animation: Framer Motion for section reveals, number count ups, and chart
  fade ins. Keep motion subtle and professional.
- Backend: a thin FastAPI service that imports the existing `pricing/` package
  and returns JSON. We do not rewrite any analytics. Endpoints:
  - `POST /diagnostic` (CSV upload to results)
  - `GET /model` (metrics and feature importance)
  - `POST /recommend` (per deal guidance)
  - `POST /summary` (LLM executive narrative)
  - `POST /map-columns` (AI column mapping)
- Auth: magic link or email allowlist for the demo; WorkOS or Auth.js for SSO
  later.
- Deploy: Next.js on Vercel; the FastAPI service on a container host (Render,
  Fly, or Cloud Run) because it carries LightGBM.

## Architecture

Two services, one source of truth for analytics.

```
pricing/            (unchanged) the analytics engine
api/  (FastAPI)     imports pricing/, returns typed JSON
web/  (Next.js)     calls api/, renders the buyer facing UI
app/  (Streamlit)   stays as the internal / fast iteration tool
```

The `pricing/` package remains the single source of truth, so the Streamlit
tool and the Next.js product never drift. The API returns the same result
shapes the engine already produces.

## Screens

1. Upload and onboard. Drag and drop a closed deal CSV. AI column mapping shown
   with readable labels and a confirm step. Clear validation messages.
2. Overview. Big plain language cards (money left on the table, price
   realization, win rate), the AI executive summary, and an animated "how it
   works" flow. This is the five second story.
3. Diagnostic. Win rate versus discount (interactive), price realization by
   segment, the leakage view, quarter end effect, governance gaps, and the
   deals to look at first.
4. Guidance. Pick a deal, see the recommended discount and the expected value,
   and a plain "why" (top factors as plus or minus on win chance, not log odds).
5. Methodology. Plain language, with the technical detail in expandable
   sections for the buyer's analyst.

## What we reuse

Everything in `pricing/` (schema, generate, ingest, metrics, model, assist) and
the brand kit in `brand/` (palette and logo become design tokens). No analytics
rewrite. The work is the API wrapper plus the front end.

## Phasing

- M0: FastAPI wrapper over the engine, typed JSON contract, one deploy.
- M1: Next.js shell, design tokens from the brand kit, Upload and Overview.
- M2: Diagnostic and Guidance screens with charts and motion.
- M3: Auth and production deploy.

## Honest tradeoff and recommendation

This is a multi week build, against hours for Streamlit. Recommendation: keep
Streamlit for internal use and quick iteration. Build the Next.js UI when one of
these is true: a design partner is close and the UI is blocking the deal, or we
are actively raising and need an investor grade product surface. In the interim,
I can de jargon the Streamlit demo in one focused pass (apply appendix A labels,
remove em dashes, hide model statistics behind an expander) so it is presentable
now without committing to the full rebuild.

## Open decisions

1. Build now, or after a design partner validates the wedge.
2. Chart library: Tremor (recommended) or Recharts.
3. Backend host for the FastAPI service: Render, Fly, or Cloud Run.

## Appendix A. Field label map (drives every table and chart)

| Field | Label |
|---|---|
| opportunity_id | Opportunity ID |
| account_name, resolved_account_name | Account |
| outcome | Outcome |
| created_date | Created |
| close_date | Close date |
| segment | Segment |
| region | Region |
| industry | Industry |
| product_tier | Plan |
| value_metric | Pricing model |
| list_acv | List value (annual) |
| booked_acv | Booked value (annual) |
| platform_fee_acv | Platform fee (annual) |
| usage_acv | Usage value (annual) |
| term_months | Term (months) |
| quantity | Quantity |
| rep_id | Rep |
| approved_by | Approved by |
| competitor_present | Competitor in deal |
| lost_reason | Lost reason |
| discount_pct | Discount % |
| price_realization | Price realization |
| discount_amount | Discount given |
| win_rate | Win rate |
| discount_band | Discount band |
| excess_discount_dollars | Excess discount |
| off_policy_unapproved | Off policy, no approval |
| is_quarter_end | Closed near quarter end |

## Appendix B. Plain language glossary (replace jargon in the UI)

| Jargon | Say instead |
|---|---|
| ACV | Annual value (annual contract value) |
| P(win) | Win probability |
| EV, expected ACV | Expected value |
| SHAP, log odds | Top factors (what pushed this up or down) |
| AUC, Brier, average precision | Group under "Model quality (advanced)" |
| Reference discount | The point where extra discount stops winning deals |
| Off policy | Above your discount policy |
