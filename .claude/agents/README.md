# Pricekeel agent fleet

Eleven project agents, invoked by name via the Agent tool. Build/GTM agents run
on Sonnet (fast, high-volume); the critic/analyst panel runs on Opus (harder
judgment). All are grounded in the vault, the Salesforce-decision-integrity
wedge, and the house rules (no em dashes in generated content; GTM agents draft
only, never send).

## Build (Sonnet)

| Agent | Expertise | Responsibilities |
|---|---|---|
| **backend-engineer** | Python pricing engine, FastAPI, tests, ML (LightGBM/SHAP) | Builds and hardens `pricing/*.py`, `api/`, `tests/`. Enforces explainability-over-accuracy, commit/ramp/overage handling, and the CRM-proxy-vs-true-margin boundary. Commits after green tests. |
| **web-engineer** | Next.js app + marketing site, brand | Builds and maintains everything under `web/`. Holds palette fidelity (`brand/PALETTE.md`), reads the Next docs first (per `web/AGENTS.md`), and keeps marketing claims inside the evidence boundary. |

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

## Graph nodes (Opus)

These two are not domain experts. They are structural nodes in the change graph, and they
run on work the other agents produce. See `docs/guides/graph-dev-workflow.md`.

| Agent | Expertise | Responsibilities |
|---|---|---|
| **ground** | Premise verification | Runs FIRST on any non-trivial change and on **every externally supplied plan**. Read-only. Labels each factual claim TRUE / FALSE / UNVERIFIABLE with `file:line` evidence, names destructive steps, and emits PROCEED / PROCEED WITH CORRECTIONS / STOP. Treats documentation as a claim, not as evidence. |
| **skeptic** | Adversarial review | Runs AFTER research or a draft plan and BEFORE implementation. Attacks unsupported claims, correlation sold as causation, scope creep, and proposals to rebuild shipped code. Emits BLOCKING / NON-BLOCKING / CLEAN. Never rewrites the work it critiques. |

## How to invoke
Name an agent in a prompt (for example: "have `pricing-strategist` review the
hero copy", or "have `cfo` and `market-sizing-analyst` rebuild the SAM"). They
can propose vault notes but do not silently commit strategy changes. NOTE: this
directory is the committed role-agent fleet; it is distinct from `.agents/`
(third-party tooling clones, gitignored).


## The change graph
Naming agents ad hoc is fine for small work. For anything non-trivial, follow
`docs/guides/graph-dev-workflow.md`: ground, then plan, then parallel review, then
skeptic, then a human gate, then implement, test, commit, record. The routing table there
says which nodes fire for which kind of change, so the ceremony scales with the stakes.

**The one rule that is not optional:** any plan you did not write, from any source, enters
at `ground` before anything else runs.
