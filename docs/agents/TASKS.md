# How to write a task

A task is the unit of work the lead assigns and the reviewer checks against.
The live board is [PROJECT_STATE.md](PROJECT_STATE.md), generated from
`project_state.json`. This file is the authoring guide.

## Required fields

| Field | Set by | Rule |
|---|---|---|
| `id` | lead | `PK-<n>`, monotonic, never reused. |
| `title` | lead | One line, imperative, names the outcome not the method. |
| `agent` | lead | One owner. Never a list. |
| `dependencies` | lead | Task ids that must be `MERGED` before this can start. |
| `owns` | lead | The narrowest set of paths or `path#component` claims that covers the work. |
| `acceptance` | product panel or lead | Checkable statements, one per line. See below. |
| `tests` | lead | The suites QA must rerun. |
| `branch` | `agentctl` | `agent/<role>/<id>`, set on assignment. |
| `worktree` | lead | `.claude/worktrees/<id>` for any task with file work. |
| `pr`, `tests.ci_run`, `review` | the gates | Never set by hand. |

## Acceptance criteria

Write them so a reviewer can mark each one true or false without asking the
author what they meant. Include the negative constraints, because those are
the ones agents violate.

Good:

- `POST /crm/compare returns at least one attributable public source per row`
- `the response never labels a CRM-derived figure as margin`
- `an empty competitor list returns 200 with an empty array, not a 500`
- `tests/test_matching.py passes, plus a new case for the empty list`

Bad:

- `competitor comparison works`
- `good test coverage`
- `follows our conventions`

## Sizing

One task is one agent, one branch, one PR, one reviewable diff. If a task
needs two agents, it is two tasks with a dependency between them. If the
acceptance list runs past six items, split it.

A task that cannot declare its owned paths up front is not ready to be
assigned. Do the investigation as its own task first.

## Decomposing a feature request

The lead's job, given something like "add competitor price monitoring":

1. Read the current architecture before planning. Do not plan against memory.
2. Ask the product panel for acceptance criteria if the requirement is
   ambiguous, rather than inventing them.
3. Split along ownership boundaries, because ownership is what makes parallel
   work safe: schema and migration, backend logic and API, AI layer, web
   surface, tests.
4. Wire dependencies in the direction data flows. Schema first, then the
   engine, then the API, then the UI. The UI task depends on the API task.
5. Declare the `owns` claim for each, and let `agentctl assign` tell you
   whether the split is actually parallel. If it refuses, the split is wrong.
6. Only tasks with no unmet dependency go to `READY`.

A worked shape:

```
PK-201 schema: competitor_price columns + migration      data-engineer
PK-202 engine: comparison logic                          backend-engineer  deps 201
PK-203 api:    POST /crm/compare                         backend-engineer  deps 202
PK-204 ai:     source attribution and narration          ai-engineer       deps 202
PK-205 web:    comparison panel                          web-engineer      deps 203
PK-206 qa:     integration + regression pass              qa-engineer       deps 203,204,205
```

PK-203 and PK-204 both touch `api/main.py`, so they claim different
components (`#crm` and `#copilot`) or they run one after the other.

## Current backlog

The live board is [PROJECT_STATE.md](PROJECT_STATE.md). Four tasks are seeded
in `BACKLOG`, none assigned:

- **PK-1 Split `api/main.py` into routers.** 1408 lines carrying six unrelated
  route groups is the largest collision surface in the repo, and it forces
  serialization on tasks that should be parallel. Doing this first makes
  everything after it cheaper. Owner: `backend-engineer`.
- **PK-2 Worktree automation in `agentctl`.** `assign` should create the
  worktree and `done` should remove it, rather than leaving both to a
  remembered command.
- **PK-3 CI verdict fetch in `agentctl`.** `approve` should call
  `gh run list --branch` itself instead of trusting a pasted run id. Depends
  on PK-2.
- **PK-4 Triage the six open PRs.** #36, #37 and #38 have been open since
  June 10 and 11 against a `main` that has moved substantially; #59, #60 and
  #61 are recent. Rebase, close, or enter as tasks. They are deliberately
  outside the task system until triaged, so the board does not inherit
  phantom state.
