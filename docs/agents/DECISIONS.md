# Architecture decision records: the agent engineering org

One decision per record, newest last. The point is to stop future agents from
relitigating a settled call. If you disagree with a record, write a superseding
one; do not quietly do the other thing.

Product and pricing decisions live in the vault (`vault/Decisions/`). This file
covers the agent workflow only.

Format: decision, context, alternatives, reason, consequences.

---

## ADR-001: Task state lives in a JSON file mutated only by a CLI

**Date:** 2026-08-29 · **Status:** accepted

**Decision.** `docs/agents/project_state.json` is the authoritative task state.
Every mutation goes through `python tools/agentctl.py`, which enforces the
transition table, the dependency gate, the ownership check, the concurrency
cap, and the merge gate. `PROJECT_STATE.md` is rendered from it and is never
hand-edited.

**Context.** Agents here have no memory between invocations. Without state on
disk, nobody can answer "why is PK-104 blocked" the next day.

**Alternatives.** GitHub Issues as the queue: real API, but every state read
becomes a network call, and the transition rules would live nowhere. A
markdown board that agents edit directly: readable, but an LLM asked to update
a status will write an illegal transition or drop a dependency, and nothing
notices. A database: unjustified for a solo pre-seed repo.

**Reason.** The rules have to be executable to be real. A refusal with an exit
code is enforcement; a sentence in a prompt is a suggestion.

**Consequences.** State changes need a shell call, which is friction on
purpose. `project_state.json` is committed, so it will conflict when two
branches both change task state; resolve by rerunning the commands rather than
merging JSON by hand. Writes are atomic (temp plus `os.replace`) because this
repo has produced torn writes.

---

## ADR-002: Git worktrees, not file locks, are the isolation mechanism

**Date:** 2026-08-29 · **Status:** accepted

**Decision.** Every task with active file work gets its own git worktree under
`.claude/worktrees/<TASK-ID>` on branch `agent/<agent-name>/<TASK-ID>`, for
example `agent/backend-engineer/PK-1`. The ownership claim in the state file
is a planning check, not the isolation mechanism.

**Context.** Subagents launched from one session share one working tree. Two
agents editing `api/main.py` in parallel means the second write wins and the
first agent's work vanishes with no error.

**Alternatives.** File-level locks in the state file alone: an agent can write
a file it did not claim, and nothing stops it, so the lock is advisory only.
Strict serialization of all work: safe, but gives up the parallelism this is
for.

**Reason.** Worktrees are the only mechanism on this platform that makes two
concurrent agents physically unable to overwrite each other. The claim check
catches the *planning* error early, before the work starts; the worktree
contains the *execution* error if the claim was wrong.

**Consequences.** A `web/**` task needs its own `npm ci`, which is slow and is
part of why the cap is low. Worktrees must be removed after merge. Conflicts
move from silent overwrite to visible merge conflict, which is the trade we
want.

---

## ADR-003: Concurrency is capped at two active coding tasks

**Date:** 2026-08-29 · **Status:** accepted

**Decision.** `config.max_concurrent` is 2. `ASSIGNED`, `IN_PROGRESS` and
`REWORK_REQUIRED` count against it. `REVIEW` and `QA` do not, because the
coding agent has stopped writing.

**Context.** This repo has a documented history of torn-write corruption
truncating working trees, and `api/main.py` plus `pricing/schema.py` are
central enough that most task pairs touch one of them.

**Alternatives.** No cap: maximum throughput, and the first bad interleaving
costs more than the parallelism saved. A cap of one: safe, and no better than
the sequential workflow that already exists.

**Reason.** Two is enough to overlap a backend task with a web task, which is
the common case, while keeping the blast radius small enough to reason about.

**Consequences.** A third ready task waits. Raise the cap deliberately, after
the worktree flow has been exercised, not because a queue looks full.

---

## ADR-004: Merging stays human, because GitHub cannot enforce it here

**Date:** 2026-08-29 · **Status:** accepted

**Decision.** `APPROVED -> MERGED` requires the `--human-approved` flag. The
product owner performs the merge. No agent merges to `main`.

**Context.** GitHub branch protection is unavailable on this plan for a
private repository, so `main` cannot be protected server-side. The API returns
403 on the protection endpoint.

**Alternatives.** Auto-merge on green CI plus reviewer approval: standard
practice on a team, and here the reviewer is the same model as the author, so
approval is weaker evidence than it looks. Making the repo public to unlock
protection: not acceptable for this codebase.

**Reason.** With no server-side gate and no independent reviewer, the human is
the only real gate. Better to name that honestly than to simulate a pipeline
that nothing enforces.

**Consequences.** The workflow is not fully autonomous, by design. The
`--human-approved` flag is a convention an agent could technically pass on its
own, so this is a trust boundary, not a security boundary. Revisit if branch
protection becomes available.

---

## ADR-005: A tool list does not make an agent read-only; Bash does not respect it

**Date:** 2026-08-29 · **Status:** accepted

**Decision.** Agents that are described as read-only, and any agent probing the
task machine's behavior, must run experiments against a scratch state
directory via `AGENTCTL_STATE_DIR`, and must never run a git command that
changes the working tree or the index. The `code-reviewer` definition states
this explicitly rather than relying on its tool list.

**Context.** This was found the hard way, on the first real review. The
reviewer was given `Read, Glob, Grep, Bash` and described in its own
definition as "read-only by design". To verify an ownership-collision finding,
which was the correct instinct and produced a genuine blocker, it ran real
`assign` and `check` commands against the live `docs/agents/project_state.json`
and then git-restored the directory to clean up after itself. A task that was
`IN_PROGRESS` with a branch, a worktree, and a file claim silently reverted to
`BACKLOG`, and the three transitions vanished from the append-only log because
the log file was restored too. The evidence was a `checkout: moving from
feat/agent-engineering-org to feat/agent-engineering-org` reflog entry and
three state files sharing an mtime ten minutes after the transitions ran.

**Alternatives.** Remove `Bash` from the reviewer: it would stop the reviewer
verifying anything by execution, and execution is exactly what turned a
plausible finding into a confirmed blocker. Make the state file read-only on
disk: breaks every legitimate write and gets chmod-ed back. Detect and refuse
concurrent mutation: real, but it does not help against a `git checkout` that
happens outside the tool entirely.

**Reason.** The capability boundary is the tool list plus what those tools can
reach. `Bash` reaches everything, so the boundary has to be stated in the
prompt and made easy to comply with. A scratch directory that costs one
environment variable is easier than the workaround the agent invented.

**Consequences.** "Read-only agent" is a description of intent in this repo,
not an enforced property, and it is now written down as such. The board can
still be clobbered by anything outside `agentctl`, which is why `check`
flags a `MERGED` task with no recorded human approval: state set outside the
tool is detectable after the fact even when it cannot be prevented. Losing the
board is recoverable by replaying commands; losing a worktree would not be,
which is another argument for ADR-002.
