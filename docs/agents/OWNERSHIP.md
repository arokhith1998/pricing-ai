# Ownership map

Who owns what. `agentctl assign` enforces the *claims* declared per task; this
file is the default assignment that tells the lead which agent a task belongs
to in the first place.

Prefer component ownership over file ownership. A claim may carry a
`#component` suffix (`api/main.py#crm`), and two disjoint components of one
file can be worked at the same time. A whole-file claim conflicts with every
component of that file, and a directory claim conflicts with everything
beneath it.

## Default owners

| Path | Owner | Notes |
|---|---|---|
| `api/**` | `backend-engineer` | HTTP perimeter, rate limiting, route handlers. |
| `pricing/metrics.py` | `backend-engineer` | The trust-critical leakage math. Known-answer tested. |
| `pricing/diagnostic.py` | `backend-engineer` | Orchestration and CLI report. |
| `pricing/governance.py` | `backend-engineer` | Decision store, exception verdicts, digest. |
| `pricing/crm.py` | `backend-engineer` | CRM-native analysis. |
| `pricing/ingest.py` | `backend-engineer` | Load, validate, identity resolution. |
| `pricing/_safe_fetch.py` | `backend-engineer` | SSRF-hardened outbound fetch. Security-sensitive. |
| `pricing/schema.py` | `data-engineer` | Canonical schema. Everything downstream speaks it. |
| `pricing/generate.py` | `data-engineer` | Synthetic generator, derived from the schema. |
| `neon/**` | `data-engineer` | Schema and dated migrations. Every up needs a down. |
| `data/**` | `data-engineer` | `data/private/` is gitignored and never committed. |
| `pricing/assist.py` | `ai-engineer` | LLM provider layer, timeouts, error mapping. |
| `pricing/copilot.py` | `ai-engineer` | Structured opportunities, canonical questions. |
| `pricing/rag.py` | `ai-engineer` | Retrieval and citation. |
| `pricing/docs.py` | `ai-engineer` | Document chunking and embeddings. |
| `pricing/mapping.py` | `ai-engineer` | Four-layer column mapper. |
| `pricing/matching.py` | `ai-engineer` | Competitor plan matching. |
| `pricing/model.py` | `ai-engineer` | LightGBM win model and SHAP explanations. |
| `web/**` | `web-engineer` | Next.js site and app, including `web/src/app/api/**`. |
| `brand/**` | `web-engineer` | Palette is canonical in `brand/PALETTE.md`. |
| `tests/**` | `qa-engineer` | Coding agents add tests for their own work; QA owns the suite. |
| `web/test/**` | `qa-engineer` | Same rule. |
| `.github/workflows/**` | `qa-engineer` | CI is the QA substrate. |
| `tools/agentctl.py` | `pk-lead` | The state machine itself. |
| `docs/agents/**` | `pk-lead` | This directory. |
| `gtm/**`, `docs/ops/**` | GTM agents | Outside the engineering task machine. |
| `vault/**` | advisory agents | Propose notes, do not silently commit strategy changes. |

## Shared hot files

These need a `#component` claim, never a whole-file claim, unless the task
genuinely rewrites the file.

### `api/main.py` (1408 lines)

One file carrying six unrelated route groups. This is the highest-collision
surface in the repo.

| Component | Rough span | Default owner |
|---|---|---|
| `#perimeter` | middleware, rate limiting, `_customer_ref` | `backend-engineer` |
| `#diagnostic` | `/demo`, `/diagnostic`, `/map-headers`, `/map-columns`, `/summary` | `backend-engineer` |
| `#model` | `/model`, `/deals`, `/recommend` | `ai-engineer` |
| `#rag` | `/docs/upload`, `/ask` | `ai-engineer` |
| `#copilot` | `/copilot/*` | `ai-engineer` |
| `#governance` | `/exceptions`, `/digest` | `backend-engineer` |
| `#crm` | `/crm/*` | `backend-engineer` |

Two tasks claiming the same component are serialized, not parallelized.
**PK-1 in the backlog splits this file into routers**, which removes the need
for most of this table.

### `pricing/schema.py`

The single source of truth for the canonical deal schema. A change here ripples
into `generate.py`, `ingest.py`, `mapping.py`, `gtm/data-request.md`, and the
synthetic fixtures. Any task touching it is a `data-engineer` task, and it
serializes against everything that reads the schema. Treat a schema change as
an ADR-worthy decision.

### `web/src/app/layout.tsx`, `web/src/components/Nav.tsx`, `web/src/app/globals.css`

Site-wide surfaces. Two web tasks touching them at once will conflict on
merge even in separate worktrees. Claim them explicitly.

## Rules

1. Declare the narrowest claim that covers the work. An unbounded claim is
   refused by `agentctl assign`.
2. Reading outside the claim is always fine. Writing outside it is a scope
   expansion the lead must grant, and an unapproved one is a review finding.
3. If two tasks genuinely need the same component, the lead picks one of:
   sequence them, split at a finer boundary, or give one task both paths and a
   single owner. It never runs both.
4. `data/private/**` and `.env` are off limits to every agent. No real
   customer data enters the repo or the vault.
