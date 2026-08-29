# Pricekeel agent fleet

Fourteen project agents, invoked by name via the Agent tool. Build agents run
on Sonnet (fast, high-volume); the lead, the reviewer, and the critic panel run
on Opus (harder judgment). All are grounded in the vault, the CRM
decision-integrity wedge, and the house rules (no em dashes in generated
content; GTM agents draft only, never send).

Six of them form a coordinated engineering org with a task state machine, file
ownership, and review and QA gates. **Read `docs/agents/AGENTS.md` for the org,
`docs/agents/WORKFLOW.md` for the lifecycle, and `docs/agents/OWNERSHIP.md` for
the file map.** The state machine is `python tools/agentctl.py`.

## Coordination (Opus)

| Agent | Expertise | Responsibilities |
|---|---|---|
| **pk-lead** | Planning, decomposition, conflict resolution | Turns a feature request into atomic tasks with owners, dependencies, acceptance criteria, and non-colliding file claims. Tracks state through `agentctl`. Writes only to `docs/agents/`. Never edits product code, never merges. |

The dispatch loop is normally run by the main session, since a subagent cannot
spawn subagents. Invoke `pk-lead` for planning and state audits in isolation.

## Build (Sonnet)

| Agent | Expertise | Responsibilities |
|---|---|---|
| **backend-engineer** | Deterministic Python engine, FastAPI | `api/**` plus `pricing/{metrics,ingest,diagnostic,governance,crm,_safe_fetch}.py`. Enforces explainability-over-accuracy, commit/ramp/overage handling, and the CRM-proxy-vs-true-margin boundary. |
| **data-engineer** | Postgres, schema, migrations, fixtures | `neon/**`, `pricing/schema.py`, `pricing/generate.py`, `data/**`. Every migration additive, transactional, rerunnable, and shipped with a down. No destructive change without authorization. |
| **ai-engineer** | LLM integration, RAG, prompts, evals, ML | `pricing/{assist,copilot,rag,docs,mapping,matching,model}.py` plus the `#model`/`#rag`/`#copilot` API routes. Holds the line that the LLM never computes a number, and that citations and timeouts are load-bearing. |
| **web-engineer** | Next.js app + marketing site, brand | Everything under `web/`. Holds palette fidelity (`brand/PALETTE.md`), reads the Next docs first (per `web/AGENTS.md`), keeps marketing claims inside the evidence boundary. |

## Verification

| Agent | Model | Responsibilities |
|---|---|---|
| **qa-engineer** | sonnet | The QA gate. Verifies acceptance criteria against real behavior, runs the suites, fetches the CI verdict, sweeps for regressions, checks migrations up and down. A green CI run id is required; an agent's claim that tests pass is not evidence. |
| **code-reviewer** | opus | The review gate. Correctness, architecture, security, maintainability, regression risk, tests, scope, and Pricekeel conventions. Read-only by design: it reports findings and a verdict, it never fixes what it finds. Escalates trust-critical diffs to `tools/oai_review.py` for a second model. |

## Go-to-market (Sonnet, drafts only)

| Agent | Expertise | Responsibilities |
|---|---|---|
| **sales-outreach** | Founder-led problem-interview outreach, ICP qualification | Sources ICP-fit accounts against the Aug 1 filters, drafts first-touch messages and interview guides, maintains the objection inventory and funnel tracker. Never sends; the founder presses send. |
| **customer-success** | Design-partner pilots, onboarding, data readiness | Runs data-readiness reviews, the $15K to $30-60K pilot motion, readout/close, benchmarking-consent language, and recurring-usage measurement. Drafts only; no customer data enters the repo. |
| **social-media-manager** | LinkedIn + Instagram, founder-brand content | Drafts posts, builds the content calendar, keeps a consistent founder-led voice per the vault LinkedIn strategy. Drafts and schedules only; never publishes or changes account settings without per-item approval. |

## Panel: critics and analysts (Opus)

| Agent | Expertise | Responsibilities |
|---|---|---|
| **cfo** | Unit economics, pricing, margin | Pressure-tests ACV/pricing, gross-margin drag from LLM inference and onboarding, CAC payback, the NRR-dependent expansion story, and market-sizing honesty. Flags any money claim that overstates. |
| **cto** | Architecture, data, security | Pressure-tests data-dependency risk, explainability posture, the Salesforce-vs-usage-data gap, security/legal gates for customer data, and time-to-value. Recommends the smallest architecture that tests the wedge. |
| **pricing-strategist** | Pricing science (Nagle, Simon-Kucher, Rivera, Ramanujam, Bertini/Koenigsberg, Simon, Poyar, Campbell) | Grounds every recommendation in a named framework and a first-class metric. Guards positioning drift, the commit/ramp/overage requirement, cold-start honesty, and methodology integrity. |
| **market-sizing-analyst** | TAM/SAM/SOM, category dynamics | Builds defensible bottoms-up market sizing, applies the real ICP funnel, separates wedge SAM from the expansion story, and refuses to let a hand-waved number enter a deck. Web-researches current figures and cites them. |

The panel sets acceptance criteria and pressure-tests decisions. It does not
modify production code unless a task explicitly assigns it.

## How to invoke

**Direct, for a one-off:** name an agent in a prompt, for example "have
`pricing-strategist` review the hero copy", or "have `cfo` and
`market-sizing-analyst` rebuild the SAM". Coding agents invoked without a task
id work in solo mode, taking their full historical surface.

**Through the task machine, for coordinated work:** the lead plans, `agentctl`
assigns and referees ownership, the agent works in its own git worktree, then
review and QA gate the PR and the human merges. Start at
`docs/agents/WORKFLOW.md`.

NOTE: this directory is the committed role-agent fleet; it is distinct from
`.agents/` (third-party tooling clones, gitignored).
