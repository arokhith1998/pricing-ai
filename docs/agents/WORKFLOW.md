# Workflow: task lifecycle, git, gates, failure recovery

Every state change goes through `python tools/agentctl.py`. Hand-editing
`project_state.json` is not allowed: the tool holds the transition table, the
ownership check, the dependency gate, the concurrency cap, and the merge gate,
and it refuses illegal moves with an exit code.

## Lifecycle

```
BACKLOG -> READY -> ASSIGNED -> IN_PROGRESS -> REVIEW -> QA -> APPROVED -> MERGED -> DONE
              ^                       |            |      |
              |                       v            v      v
              +------------- REWORK_REQUIRED <-----+------+
              |
   BLOCKED <--+--> FAILED
```

| Transition | Gate the tool enforces |
|---|---|
| `BACKLOG -> READY` | Every dependency is `MERGED` or `DONE`, and an owner agent is set. |
| `READY -> ASSIGNED` | Declared paths do not collide with any live claim, and active work is under the cap. |
| `ASSIGNED -> IN_PROGRESS` | None. The agent has started. |
| `IN_PROGRESS -> REVIEW` | A PR number. Not a claim of doneness. |
| `REVIEW -> QA` | A reviewer verdict of `approve` or `approve-with-nits`. `reject` routes to `REWORK_REQUIRED`. |
| `QA -> APPROVED` | A green CI run id. An agent reporting that tests pass is not evidence. |
| `APPROVED -> MERGED` | `--human-approved`. No agent merges to main on its own authority. |
| `MERGED -> DONE` | None. Releases the ownership claim. |

`FAILED` and `DONE` release the claim. `BLOCKED` keeps it, because the work is
paused rather than abandoned.

## Command reference

```powershell
$env:PYTHONPATH = "C:\Pricing-AI"

python tools/agentctl.py add PK-104 "Add competitor price comparison" `
    --agent backend-engineer --depends PK-101 `
    --acceptance "POST /crm/compare returns cited public sources" `
    --acceptance "no true-margin claim in the response or the copy" `
    --test tests/test_matching.py

python tools/agentctl.py ready   PK-104
python tools/agentctl.py assign  PK-104 --own pricing/matching.py --own "api/main.py#crm"
python tools/agentctl.py start   PK-104
python tools/agentctl.py review  PK-104 --pr 62
python tools/agentctl.py qa      PK-104 --verdict approve --by code-reviewer
python tools/agentctl.py approve PK-104 --ci-run 30761095888
python tools/agentctl.py merged  PK-104 --commit abc1234 --human-approved
python tools/agentctl.py done    PK-104

python tools/agentctl.py status              # the whole board
python tools/agentctl.py status --id PK-104  # one task, including why it is blocked
python tools/agentctl.py log -n 40           # what happened, in order
python tools/agentctl.py check               # validate every invariant
```

## Git and isolation

Branch name: `agent/<role>/<TASK-ID>`, for example `agent/backend/PK-104`.
`agentctl assign` sets it automatically from the owner agent and task id.

Each task with active file work gets its own git worktree so that two agents
never share a checkout:

```powershell
git fetch origin
git worktree add .claude/worktrees/PK-104 -b agent/backend/PK-104 origin/main
python tools/agentctl.py assign PK-104 --worktree .claude/worktrees/PK-104 --own pricing/matching.py
```

`.claude/worktrees/` is gitignored. Remove the worktree after merge:
`git worktree remove .claude/worktrees/PK-104`.

Two notes that matter in practice. A `web/**` task needs its own `npm ci` in
the worktree, which is why the concurrency cap is low. And the standing repo
rule applies inside worktrees too: commit immediately after every green test
run and push, because torn writes have truncated working trees here before.

**`main` is not protected server-side.** GitHub branch protection is
unavailable on this plan for a private repo, so "no autonomous merge to main"
is enforced by the `--human-approved` gate and by convention, not by GitHub.
Treat that as a known weakness, not a solved problem.

## PR pipeline

```
agent -> commit -> push -> PR -> code-reviewer -> qa-engineer -> fixes if needed -> human approval -> merge
```

The PR body follows `.github/pull_request_template.md`: Summary, Why,
Implementation, Tests, Risks, Dependencies. The task id goes in the PR title.
CI runs on every push to every branch, so a PR arrives with a verdict already.

## Review gate

The reviewer evaluates, in this order, and states a verdict of `approve`,
`approve-with-nits`, or `reject` with reasons:

1. **Correctness.** Does it satisfy every acceptance criterion, actually?
2. **Architecture.** Does it fit the existing structure, or bolt a second
   pattern beside a working one?
3. **Security.** The `api/main.py` perimeter and rate limits, OAuth token
   encryption, the SSRF guard in `pricing/_safe_fetch.py`, tenant scoping, and
   anything that touches secrets or customer data.
4. **Maintainability.** Unnecessary complexity, duplicated logic, dead code.
5. **Regression risk.** What existing behavior could this break?
6. **Tests.** Sufficient for business logic, pipelines, and ML or LLM evals.
   Trivial CRUD does not need them.
7. **Scope.** Did the agent touch anything outside its owned paths? Any
   out-of-scope edit is a finding by definition.
8. **Pricekeel conventions.** Explainability over accuracy, no CRM proxy
   labeled as margin, commit and ramp and overage handled, no em dashes, no
   fabricated traction.

For trust-critical diffs run `python tools/oai_review.py --diff` and fold the
second-model findings in. Never send customer data through it.

## QA gate

1. Re-run the task's required suites locally and paste the real output.
2. Fetch the CI verdict: `gh run list --branch agent/backend/PK-104 --limit 3`.
   A green run id is required to leave QA.
3. Check each acceptance criterion against real behavior, not against the
   diff's intent.
4. Run the full Python suite for regressions, plus `npm test`, `npx eslint`,
   `npx tsc --noEmit` and `npm run build` in `web/` for web tasks.
5. Migrations get an up and a down applied against a scratch database. Every
   file in `neon/migrations/` has a `.down.sql` for this reason.
6. Report failures with the actual output. Never round a failure up to a pass.

## Failure recovery

An agent must report failure rather than describe a success it did not
achieve. Named failure modes and the response:

| Failure | Response |
|---|---|
| Tool or command failure | Report the exact error. Do not retry the same call more than twice. |
| Test failure | Stay in `IN_PROGRESS`, fix, rerun. If the cause is outside the owned paths, `block` and report. |
| Merge conflict or stale branch | Rebase on `origin/main` inside the worktree. If the conflict is in another task's owned file, `block` and hand it to the lead. |
| Dependency failure | `block --reason` naming the blocking task id. |
| API or provider failure | Report and stop. Do not fabricate the response. |
| Agent timeout or incomplete work | The lead runs `fail --reason`, which releases the claim, then reassigns. |
| Hallucinated file or function | A review finding. Route to `REWORK_REQUIRED`. |
| Conflicting architectural change | Stop, write an ADR proposal in `DECISIONS.md`, let the lead decide. |

`fail` releases the ownership claim so the work can be reassigned to another
agent without a manual cleanup.

## Human control

Agents may inspect, plan, implement, test, review, create branches and
worktrees, open PRs, and update task state. Agents may **not**, without
explicit per-item authorization:

- run destructive database changes or delete production resources
- change or expose secrets, or touch production credentials
- merge to `main`
- deploy, or trigger anything customer-facing
- send an email, message, or post

The product owner is the final approver on every merge.
