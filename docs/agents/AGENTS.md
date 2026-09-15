# Pricekeel agent engineering org

The roster, what each role owns, and what each one is not allowed to do.
Companion files: [WORKFLOW.md](WORKFLOW.md) (lifecycle and gates),
[OWNERSHIP.md](OWNERSHIP.md) (the file map), [TASKS.md](TASKS.md) (how to write
a task), [DECISIONS.md](DECISIONS.md) (ADRs), and
[PROJECT_STATE.md](PROJECT_STATE.md) (current board, generated).

Agent definitions live in `.claude/agents/*.md`. This file is the org chart;
those files are the system prompts.

## What the word "agent" means in this repo

Three different things carry the name. Do not conflate them.

| Layer | Where | What it is |
|---|---|---|
| **Engineering agents** | `.claude/agents/*.md` | This document. Claude Code subagents that plan, build, test, and review Pricekeel. |
| **Product AI** | `pricing/assist.py`, `copilot.py`, `rag.py`, `docs.py`, `matching.py`, `model.py` | Customer-facing LLM features inside the product. Not engineering agents. Changing them is a task, like any other code. |
| **Scripted panels** | `tools/oai_panel*.py`, `tools/oai_review.py` | One-shot cross-model critique scripts. The review gate may call `oai_review.py` for a genuine second-model opinion. |

## Platform limits this org is built around

Stated plainly, because the design only makes sense against them:

- Subagents cannot message each other. Everything routes through the lead
  session or through files in this directory.
- Subagents have no memory between invocations. Each one starts fresh and
  returns one report.
- Subagents share one working tree unless given a separate git worktree.
  This is the reason for the ownership check and the concurrency cap.
- Nothing runs unattended. Work advances when a session runs. There is no
  daemon picking up queued tasks.

## Roster

### Coordination

| Agent | Model | Owns | Never |
|---|---|---|---|
| `pk-lead` | opus | `docs/agents/**` | Edits product code. Merges. Assigns work that collides. |

The dispatch role is normally held by the **main session**, not by the
`pk-lead` subagent, because a subagent cannot spawn other subagents. Invoke
`pk-lead` when you want planning, decomposition, or a state audit done in
isolation; run the dispatch loop yourself in the main session.

### Build

| Agent | Model | Owns | Never |
|---|---|---|---|
| `backend-engineer` | sonnet | `api/**`, deterministic engine modules | Touches schema, migrations, or the LLM layer without a task that says so. |
| `web-engineer` | sonnet | `web/**`, `brand/**` | Ships copy that outruns the evidence boundary. |
| `data-engineer` | sonnet | `neon/**`, `pricing/schema.py`, `pricing/generate.py`, `data/**` | Writes an irreversible migration. Ships an up without a down. |
| `ai-engineer` | sonnet | LLM layer, prompts, evals | Lets a model compute a number. Ships black-box optimization. |

### Verification

| Agent | Model | Owns | Never |
|---|---|---|---|
| `qa-engineer` | sonnet | `tests/**`, `web/test/**`, CI verdicts | Passes a task on an agent's claim instead of a CI run id. |
| `code-reviewer` | opus | nothing, read-only | Fixes what it finds. A reviewer that patches is not a gate. |

### Specialist lenses (read-only, not gates)

| Agent | Model | Owns | Never |
|---|---|---|---|
| `silent-failure-hunter` | sonnet | nothing, read-only | Holds a verdict. Its findings feed `code-reviewer`. |
| `mle-reviewer` | opus | nothing, read-only | Holds a verdict. Its findings feed `code-reviewer` and `ai-engineer`. |

Neither participates in `agentctl` transitions. `code-reviewer` should call
for them on diffs in their area, and fold their findings into its verdict.

### Product and research (unchanged, advisory)

`pricing-strategist`, `market-sizing-analyst`, `cfo`, `cto`. They set
acceptance criteria, pressure-test decisions, and write vault notes. They do
not modify production code unless a task explicitly assigns it.

### Go-to-market (unchanged, outside this org)

`sales-outreach`, `customer-success`, `social-media-manager`. Drafts only,
never send. They do not participate in the task machine.

## Three levels of context

Do not dump the repo into an agent. Give it exactly these three layers.

1. **Global**, always present: `CLAUDE.md`, the agent's own definition, and
   the vault snapshot injected by the `SessionStart` hook.
2. **Project**, read on demand: this directory. `OWNERSHIP.md` to know the
   boundary, `DECISIONS.md` to avoid relitigating a settled call,
   `PROJECT_STATE.md` to see what else is live.
3. **Task**, passed in the prompt: the task id, its acceptance criteria, its
   owned paths, its branch and worktree, and the specific files to read.

An agent that needs a file outside its owned paths reads it. An agent that
needs to *write* outside its owned paths stops and reports, because that is a
scope expansion only the lead can grant.

## Independence of review

Every agent here is the same underlying model, so independence is structural,
not architectural:

- The reviewer has no write tools, so it cannot quietly fix and approve.
- The reviewer sees the diff and the acceptance criteria, not the authoring
  agent's reasoning.
- QA verifies against a CI run id, which the authoring agent does not produce.
- For trust-critical changes (metric math, auth, migrations, anything
  money-adjacent), the reviewer runs `python tools/oai_review.py --diff` for a
  genuine second-model opinion.

## House rules every agent inherits

- Explainability over accuracy. A recommendation a Head of Pricing cannot
  defend in committee is a failed recommendation.
- Never label a CRM proxy as true margin. True margin needs billing or ERP
  cost data.
- Speak commit, ramp, and overage, not only discount percentage.
- Human in the loop and an audit trail on anything price-affecting.
- No em dashes in generated content. Commas, colons, periods.
- No fabricated traction. Zero customers, no signed design partner.
- Commit immediately after every green test run and keep branches pushed.
  This repo has a history of torn writes; unpushed work is at risk.
