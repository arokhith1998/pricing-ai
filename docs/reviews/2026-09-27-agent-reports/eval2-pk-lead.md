# Pricekeel state audit, lead lens, 2026-09-27

## Verdict
Checkout is current (0 behind main). `agentctl check` is green but the board is stale: PR #69 (104 files, CI 36295033618 green) closed work still listed READY or BACKLOG and absorbed the orphan time-split branch, whose branch and worktree survive. Critical path unchanged: `funnel-tracker.csv` is header only.

## Board versus reality (inspected on HEAD)
| Task | Board | Reality |
|---|---|---|
| PK-14 | READY | Closed: GuidanceClient:74, :347-352 conditional. |
| PK-16 | BACKLOG | Closed: BU and product-line references; non-additivity pinned, test_copilot.py:271. |
| PK-6 | READY | Half: licenses/page.tsx:40 lists openai; incident-response.md:17 names OpenAI; DPA link is generic. |
| PK-12 | READY | One of three: checklist:97 and seed-deck:98 untouched. |
| PK-7 | READY | Untouched. |
| Orphan branch | none | Content on main; branch and worktree fix-model-silent survive, clean. Delete. |
| OWNERSHIP.md:50-67 | | Stale: main.py is 383 lines plus eight routers. |
| ADR-006 | | Absent. |

## Open PRs (merge-tree against origin/main)
- #36, #37: already on main (cf19659). Close.
- #38 landing-v2: conflicts in page.tsx, Footer, Nav; superseded by PK-21. Close.
- #59 link tracking: one conflict, off by default. Founder call.
- #60 operating manual: one conflict. Rebase and merge; CLAUDE.md:4,67 still claim no product code.
- #61 tenant key: stacked on feat/crm-provider-schema (6 commits, no PR), conflicts in schema.sql; #69 shipped a per-visitor tenant. Close, re-scope as PK-22.

## Reconciliation commands (text only, in order, cap 2; prefix `python tools/`)
```
agentctl assign PK-14 --own web/src/components/GuidanceClient.tsx --own web/src/app/diagnostic/page.tsx --branch fix/agent-eval-findings
agentctl start PK-14
agentctl review PK-14 --pr 69
agentctl qa PK-14 --verdict approve --by code-reviewer --notes "closed inside PR #69"
agentctl approve PK-14 --ci-run 36295033618
agentctl merged PK-14 --commit cf37f27 --human-approved --approver "adhithya, PR #69, 2026-09-27"
agentctl done PK-14
agentctl ready PK-16   (then the same seven steps, --own pricing/copilot.py --own tests/test_copilot.py)
agentctl fail PK-6 --reason "AC1-2 closed by PR #69 outside the board; residual is PK-17"
agentctl fail PK-12 --reason "AC1 closed by PR #69; residual is PK-18"
agentctl add PK-17 "Finish Anthropic disclosures" --agent web-engineer --own web/src/app/licenses --own docs/ops/incident-response.md --acceptance "no openai on either surface; DPA URL is Anthropic's, dated"
agentctl add PK-18 "Checklist:97 and seed-deck:98 credential" --agent web-engineer --own docs/reviews/founder-action-checklist.md --own vault/GTM/seed-deck-outline.md --acceptance "credential matches the site"
agentctl add PK-19 "OWNERSHIP.md router map" --agent pk-lead --own docs/agents/OWNERSHIP.md --acceptance "no api/main.py#component span remains"
agentctl add PK-20 "ADR-006 monotone constraint" --agent pk-lead --own docs/agents/DECISIONS.md --acceptance "states why AUC 0.640 to 0.619 is accepted"
agentctl add PK-21 "Landing page rework" --agent web-engineer --own web/src/app/page.tsx --own web/src/components/HeroHeadline.tsx --own web/src/components/WhatYouGet.tsx --acceptance "one CTA verbatim; usage/hybrid claim matches the finding-6 decision; every figure traces to /sample; no em or en dashes; green npm test, eslint, tsc, build"
agentctl ready PK-4 / PK-17 / PK-18 / PK-19 / PK-20 / PK-21   (one call each)
```

## PR #62 split
- **#62a org, merge first:** `.claude/agents/*`, `.github/*`, `.gitignore`, `docs/agents/**`, `tools/agentctl.py`, `tests/test_agentctl.py`. Acceptance: `check` green from fresh main.
- **#62b:** four web files (ICP $20M to $10M) fold into PK-21.
- **#62c GTM:** `gtm/llama-ventures/*` and the three deck scripts, after the arithmetic fix.

## Two weeks toward a paid pilot
| # | Task | Owner | Acceptance |
|---|---|---|---|
| 1 | Reconcile board; delete orphan branch and worktree | pk-lead plans, founder runs | PK-14, PK-16 DONE; worktree gone |
| 2 | Merge #62a; close #36, #37, #38, #61; rebase #60 | founder | main holds docs/agents; 3 open PRs or fewer |
| 3 | PK-19, then PK-20 | pk-lead | router map; ADR-006 |
| 4 | Finding-6 decision: V1 governs contract-value discount, or build the value-metric cell | pricing-strategist advises, founder decides | one line in DECISIONS.md |
| 5 | PK-21 landing rework | web-engineer | PK-21 acceptance; #38 closed |
| 6 | PK-17, PK-18, PK-7 | web-engineer, ai-engineer | no OpenAI on any customer surface |
| 7 | PK-22 per-user actor identity, design doc first | backend-engineer | visitors cannot read each other's exceptions; failed audit write returns 503 |
| 8 | 2GP Salesforce package in a scratch org | backend-engineer | installs in an org the founder does not own |
| 9 | Five interviews, signable NDA, a price on the pricing page | founder; sales-outreach drafts | five real funnel rows; legal.ts entity unbracketed; one price visible |

Parallel: 3 with 5; 6 with 7. Sequenced: 4 before 5. Item 9 gates the pilot.

Inspected: board, `check`, `status`, `gh pr list`, merge-tree, every file cited. Not re-executed: the PK-16 slice reference.
