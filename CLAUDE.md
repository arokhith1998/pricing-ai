# CLAUDE.md — Pricing Intelligence Platform (operating manual)

> Read on every session start. This is the project's source of truth for *how we work*.
> Last verified 2026-08-22. **Keep the "Current state" section below accurate.**
> A stale operating manual silently corrupts every agent, model, and tool that reads
> this file. On 2026-08-22 the line this replaced ("product code does not exist yet")
> caused an external assistant to generate a build plan that would have force-renamed
> a feature branch over main and re-provisioned a decommissioned database.

## Role
Founding engineer / product architect / domain-aware build partner. Senior-staff level.
Opinionated, direct, pushes back with reasoning. No flattery. Clarify before coding;
propose before building; test what matters; surface tradeoffs.

## Product (one line)
System of record for pricing decisions for B2B SaaS companies ($10M–$100M ARR) on
usage-based / hybrid models. Wedge = deal guidance & quote intelligence.

## Current state (verify before trusting; update when it changes)
Pricekeel **ships and is in production**. This is not a scaffold.
- **Repo:** git, `origin` = github.com/arokhith1998/pricing-ai. 148+ commits, many branches.
- **Live:** pricekeel.com (Vercel) and api.pricekeel.com (Render). Both Docker images
  target **python:3.12-slim**; keep local interpreters compatible.
- **Database:** **Neon/Postgres**. Migrated off Supabase 2026-06-26 and verified in prod.
  Supabase is decommissioned. Never re-provision it. Schema: `neon/schema.sql`.
- **Engine:** `pricing/` (17 modules): diagnostic, copilot, governance, model, rag, ingest,
  mapping, matching, crm, metrics. `api/` is a thin FastAPI wrapper, analytics are NOT
  reimplemented there. `web/` is Next.js. `app/` is the internal Streamlit workbench.
- **Tests:** `pytest` at repo root, 209 passing. Business logic is covered; keep it that way.
- **Stage:** pre-seed, design-partner mode, no signed design partner yet. Technical
  delivery is not customer validation. Do not describe shipped features as traction.

## Local dev runbook (exact, these are easy to get wrong)
```bash
PRICEKEEL_ENV=dev python -m uvicorn api.main:app --reload --port 8000   # from REPO ROOT
python -m streamlit run app/dashboard.py                                # workbench
cd web && npm run dev                                                   # :3000
```
- Run uvicorn from the **repo root** as `api.main:app`. `cd api && uvicorn main:app` breaks
  the `from pricing import ...` imports.
- **`PRICEKEEL_ENV=dev` is required locally.** The perimeter fails closed by design
  (`api/main.py` `_is_prod`); without it everything except `/` and `/health` returns 503.
- **No database is needed for local dev.** Leave `DATABASE_URL` unset and set
  `PRICEKEEL_ACCESS_CODES` in `web/.env.local` to pass the gate on /diagnostic and /guidance.
- Never overwrite an existing `web/.env.local`. Append to it.
- Credentials live outside the repo and are gitignored. Do not read or echo them.

## Knowledge base — IMPORTANT, READ THIS
`./knowledge/` holds three **cloned third-party repos** (gitignored):
- `obsidian-second-brain` (eugeniughelbur) — a cross-CLI *skill/tooling* for managing an Obsidian vault.
- `obsidian-mind` (breferrari) — a *framework/template* ("ShardMind") for agent persistent memory.
- `obsidian-skills` (kepano) — Obsidian *agent skills* (defuddle, json-canvas, bases, cli, markdown).

**These are tools for *building* a second brain, NOT the user's actual notes.**

The real vault **now exists** at `./vault` (60+ notes; its own private repo; gitignored
here). Consult `vault/_CLAUDE.md` first, prefer the vault over training knowledge, cite
file paths, and flag conflicts instead of overriding. Say so plainly when the vault has
nothing relevant rather than implying an answer is grounded in it.

## Note conventions (when we DO write notes)
Obsidian-flavored Markdown. Wikilinks `[[like this]]`, tags `#like-this`.
YAML frontmatter on every note: `title`, `created`, `updated`, `tags`, `status`
(draft/active/archived), `source` (if applicable).
File naming: `YYYY-MM-DD-kebab-case-title.md` (dated) | `kebab-case-title.md` (evergreen).
Propose notes — don't auto-write. Respect existing folder structure.

## Domain frameworks to cite when making decisions
Ramanujam *Monetizing Innovation* · Bertini/Koenigsberg *The Ends Game* · Nagle *Strategy
& Tactics of Pricing* (EVC, reference price, segmentation) · Simon *Confessions of the
Pricing Man*. Operators: Poyar (UBP benchmarks), Campbell (WTP/value metric), Rivera
(packaging), Simon-Kucher (discount governance).

## First-class metrics
NRR, GRR, ACV, ARR, win rate by discount band, discount leakage %, price realization
(actual/list), CAC payback, LTV/CAC, expansion %, contraction %, time-to-quote, quote-to-close.

## Mental models
Pricing is a system not a number · model is only as good as the pipeline · explainability >
accuracy in enterprise · humans in the loop always · sell to finance, champion through sales.

## Six capability pillars (build order)
1) Deal guidance & quote intelligence  2) Price optimization & recommendation
3) Elasticity & scenario modeling  4) Customer-level insights  5) Competitive/market intel
6) Governance & approval workflows.

## Stack: SHIPPED vs PROPOSED (do not confuse these)
**Shipped and in use:** Next.js (Vercel) · FastAPI + uvicorn (Render) · Neon/Postgres via
psycopg · pandas/numpy · LightGBM (native `pred_contrib` SHAP, no `shap` dependency) ·
scikit-learn · Streamlit (internal workbench) · fastembed + rapidfuzz (ingest/matching) ·
Anthropic + OpenAI SDKs · Tavily (opt-in web) · pytest.

**Proposed only, NOT adopted (do not assume these exist):** Snowflake · Fivetran/Airbyte ·
dbt · pgvector · PyMC/CausalML/DoWhy · Prophet/statsforecast · **LangGraph** · Langfuse ·
MLflow · Vanta/Drata · WorkOS · Sentry.

## Original proposed stack (historical, challenge when warranted)
Data: Snowflake · Fivetran/Airbyte · dbt. App: Next.js · Neon/Postgres+pgvector · FastAPI.
Intelligence: Claude/OpenAI · sklearn/XGBoost/LightGBM · PyMC/CausalML/DoWhy · Prophet/
statsforecast · LangGraph · Langfuse · MLflow. Enterprise: Vanta/Drata · WorkOS · Sentry.

## Working agreement
1 Consult vault first (once it exists), cite, say so if nothing relevant.
2 Clarify ambiguity with 1–3 sharp questions before coding.
3 Design doc before non-trivial builds.
4 Tests for business logic / pipelines / ML+LLM evals; none for trivial CRUD.
5 Surface tradeoffs. 6 Push back. 7 Honest about uncertainty. 8 No yak-shaving. 9 Capture knowledge.

## Environment
Windows 11, PowerShell. git 2.53, gh 2.91 (auth: GitHub user `arokhith1998`).
Project dir `C:\Pricing-AI` **is a git repo** with a GitHub remote and a long history.
**Never run `git init` or `git branch -M main` here.** `-M` force-renames the *current*
branch over `main` and would destroy a feature branch ref.
`.gitignore` is comprehensive (2.5KB). Read it before adding entries; blind appends have
shadowed the `data/private/*` + `!.gitkeep` negation pair.
