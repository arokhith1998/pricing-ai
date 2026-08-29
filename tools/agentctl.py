"""agentctl - the task state machine for the Pricekeel agent engineering org.

Why this exists as a tool and not as a convention: a JSON state file that
agents hand-edit rots within a day. An LLM asked to "update the status" will
cheerfully write an illegal transition, drop a dependency, or claim a file
another task already owns, and nothing notices until two branches have
overwritten each other. Every mutation therefore goes through here, where the
transition table, the ownership check, and the concurrency cap are enforced in
code and a refusal is an exit code rather than a suggestion.

Reads and writes `docs/agents/project_state.json` (authoritative),
`docs/agents/activity.jsonl` (append-only history), and renders
`docs/agents/PROJECT_STATE.md` (derived, never hand-edited).

Writes are atomic (temp file plus os.replace) because this repo has a history
of torn writes truncating files after a commit.

Usage (see `python tools/agentctl.py --help` for the full surface):

  python tools/agentctl.py add PK-104 "Add competitor price comparison"
      --agent backend-engineer --depends PK-101
  python tools/agentctl.py ready PK-104
  python tools/agentctl.py assign PK-104 --own pricing/matching.py
  python tools/agentctl.py start PK-104
  python tools/agentctl.py review PK-104 --pr 62
  python tools/agentctl.py qa PK-104 --verdict approve
  python tools/agentctl.py approve PK-104 --ci-run 30761095888
  python tools/agentctl.py merged PK-104 --commit abc1234 --human-approved
  python tools/agentctl.py status
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Point this at a scratch directory to experiment without touching the live
# board. This exists because it was needed: a review agent verified a finding
# by running real `assign` and `check` commands against the real state file,
# then git-restored the directory to clean up, and a live task lost its
# branch, worktree, and claim. Anyone probing behavior uses this, not the
# board. See docs/agents/DECISIONS.md ADR-005.
AGENT_DIR = Path(os.environ.get("AGENTCTL_STATE_DIR",
                                PROJECT_ROOT / "docs" / "agents"))
STATE_PATH = AGENT_DIR / "project_state.json"
LOG_PATH = AGENT_DIR / "activity.jsonl"
RENDER_PATH = AGENT_DIR / "PROJECT_STATE.md"

TASK_ID_RE = re.compile(r"^PK-\d+$")

# --- the state machine -------------------------------------------------------
# Every legal edge. Anything not listed here is refused, which is the whole
# point of routing mutations through this file.

TRANSITIONS: dict[str, set[str]] = {
    "BACKLOG": {"READY", "BLOCKED", "FAILED"},
    "READY": {"ASSIGNED", "BACKLOG", "BLOCKED", "FAILED"},
    "ASSIGNED": {"IN_PROGRESS", "READY", "BLOCKED", "FAILED"},
    "IN_PROGRESS": {"REVIEW", "BLOCKED", "FAILED", "REWORK_REQUIRED"},
    "REVIEW": {"QA", "REWORK_REQUIRED", "BLOCKED", "FAILED"},
    "QA": {"APPROVED", "REWORK_REQUIRED", "BLOCKED", "FAILED"},
    "APPROVED": {"MERGED", "REWORK_REQUIRED", "BLOCKED"},
    "MERGED": {"DONE"},
    "DONE": set(),
    "BLOCKED": {"READY", "ASSIGNED", "IN_PROGRESS", "FAILED", "BACKLOG"},
    "FAILED": {"BACKLOG", "READY"},
    "REWORK_REQUIRED": {"IN_PROGRESS", "BLOCKED", "FAILED"},
}

STATUSES = set(TRANSITIONS)

# Statuses that hold a live claim on files. A task in one of these owns its
# paths and no other task may claim an overlapping path.
CLAIMING = {"ASSIGNED", "IN_PROGRESS", "REVIEW", "QA", "APPROVED",
            "REWORK_REQUIRED", "BLOCKED"}

# Statuses that count against the concurrency cap. Review and QA do not: the
# coding agent has stopped writing, so the cap is about simultaneous editing.
ACTIVE_WORK = {"ASSIGNED", "IN_PROGRESS", "REWORK_REQUIRED"}

# A dependency is satisfied only once it is on main.
SATISFIED = {"MERGED", "DONE"}

REVIEW_VERDICTS = {"approve", "approve-with-nits", "reject"}


class Refused(RuntimeError):
    """A mutation the state machine will not perform. Exit code 1."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- persistence -------------------------------------------------------------

def default_state() -> dict:
    return {
        "version": 1,
        "objective": "",
        "sprint": "",
        "updated": _now(),
        "config": {"max_concurrent": 2},
        "tasks": [],
    }


def load_state(path: Path | None = None) -> dict:
    # Resolved at call time, not at def time, so tests can repoint STATE_PATH.
    path = path or STATE_PATH
    if not path.exists():
        return default_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Refused(f"{path} is not valid JSON: {exc}. Repair it by hand "
                      "or restore from git before continuing.") from exc
    state.setdefault("config", {}).setdefault("max_concurrent", 2)
    state.setdefault("tasks", [])
    validate_tasks(state)
    return state


def _atomic_write(path: Path, text: str) -> None:
    """Write via a temp file in the same directory, then os.replace.

    A partially written state file is worse than no state file, and this repo
    has produced truncated working-tree files before.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name,
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# Events queued by a mutation and flushed only after the state write succeeds.
# The history must not record a transition that failed to persist: on Windows
# `os.replace` raises PermissionError when a sync client holds the destination,
# which is exactly the environment this repo documents.
_PENDING_EVENTS: list[tuple[str, str | None, str | None, str]] = []


def queue_event(event: str, task: str | None, agent: str | None,
                detail: str) -> None:
    _PENDING_EVENTS.append((event, task, agent, detail))


def flush_events() -> None:
    global _PENDING_EVENTS
    pending, _PENDING_EVENTS = _PENDING_EVENTS, []
    for row in pending:
        log_event(*row)


def save_state(state: dict, path: Path | None = None) -> None:
    path = path or STATE_PATH
    state["updated"] = _now()
    _atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    flush_events()


def log_event(event: str, task: str | None, agent: str | None, detail: str,
              path: Path | None = None) -> None:
    """Append one line to the activity log. Append-only, never rewritten."""
    path = path or LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": _now(), "event": event, "task": task,
           "agent": agent, "detail": detail}
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# --- ownership ---------------------------------------------------------------

_GLOB_CHARS = set("*?[]")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def normalize_path(raw: str) -> str:
    """Canonical repo-relative form of an owned path, plus optional `#component`.

    Canonicalization is not cosmetic: `paths_conflict` compares these strings,
    so any spelling variance of one file reads as two files and two agents get
    assigned the same file with no collision reported. `api/main.py` versus
    `API/main.py` is the likely case on this Windows repo, where the two names
    are one file.

    Refuses what cannot be a repo-relative claim: absolute paths, drive-
    qualified paths, parent traversal, and glob patterns (an unbounded claim
    cannot be collision-checked, which is the point of declaring one).
    """
    p = raw.strip().replace("\\", "/")
    file_part, _, comp = p.partition("#")
    file_part, comp = file_part.strip(), comp.strip()

    if _DRIVE_RE.match(file_part) or file_part.startswith("/"):
        raise Refused(f"Ownership paths are repo-relative, got {raw!r}. "
                      "Drop the drive letter or leading slash.")
    if any(ch in _GLOB_CHARS for ch in file_part):
        raise Refused(f"Ownership paths cannot be glob patterns, got {raw!r}. "
                      "Name the directory or the files.")

    segments: list[str] = []
    for seg in file_part.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            raise Refused(f"Ownership paths cannot traverse upward, got {raw!r}.")
        segments.append(seg)
    if not segments:
        raise Refused(f"Not a usable ownership path: {raw!r}")

    cleaned = "/".join(segments)
    return f"{cleaned}#{comp}" if comp else cleaned


def _fold(path: str) -> str:
    """Comparison key. Case-insensitive, because this repo runs on Windows and
    a case-only difference names the same file. Over-matching serializes two
    tasks; under-matching loses an agent's work, so fold."""
    return path.lower()


def paths_conflict(a: str, b: str) -> bool:
    """True when two ownership claims cannot be held at the same time.

    Directory claims subsume the files beneath them: owning `web/` conflicts
    with owning `web/src/app/page.tsx`. Component claims on the same file are
    disjoint from each other (`api/main.py#crm` vs `api/main.py#copilot`) but
    a whole-file claim conflicts with every component of that file. Component
    ownership is what makes `api/main.py`, a 1400-line file carrying six
    unrelated route groups, shareable at all.
    """
    fa, _, ca = _fold(a).partition("#")
    fb, _, cb = _fold(b).partition("#")
    if fa == fb:
        return not (ca and cb) or ca == cb
    # Directory containment, on path-segment boundaries only, so that
    # `web/src` never accidentally subsumes `web/src-legacy`.
    return fa.startswith(fb + "/") or fb.startswith(fa + "/")


def find_collisions(state: dict, task_id: str,
                    paths: list[str]) -> list[tuple[str, str, str]]:
    """(other_task_id, their_path, our_path) for every live conflicting claim."""
    out: list[tuple[str, str, str]] = []
    for other in state["tasks"]:
        if other["id"] == task_id or other["status"] not in CLAIMING:
            continue
        for theirs in other.get("owns", []):
            for ours in paths:
                if paths_conflict(theirs, ours):
                    out.append((other["id"], theirs, ours))
    return out


# --- task helpers ------------------------------------------------------------

def get_task(state: dict, task_id: str) -> dict:
    for t in state["tasks"]:
        if t["id"] == task_id:
            return t
    raise Refused(f"No such task: {task_id}")


def set_status(state: dict, task: dict, new: str, *, note: str = "",
               force: bool = False) -> None:
    old = task["status"]
    if new not in STATUSES:
        raise Refused(f"Unknown status: {new}")
    if new not in TRANSITIONS[old]:
        legal = ", ".join(sorted(TRANSITIONS[old])) or "nothing, it is terminal"
        raise Refused(f"{task['id']}: {old} -> {new} is not a legal transition. "
                      f"From {old} you may go to: {legal}.")
    # The cap is enforced here rather than in `assign` alone, because assign is
    # not the only door into active work: unblock, rework, and a rejected
    # review all push a task back into it, and a rejected review is routine.
    if new in ACTIVE_WORK and old not in ACTIVE_WORK and not force:
        cap = state["config"]["max_concurrent"]
        if active_count(state, exclude=task["id"]) >= cap:
            raise Refused(
                f"{task['id']}: concurrency cap reached, {cap} tasks are "
                f"already in active work, so {old} -> {new} is refused. "
                "Finish or park one first. The cap exists because parallel "
                "agents sharing one checkout overwrite each other. "
                "Pass --force only with a deliberate reason.")
    task["status"] = new
    task["updated"] = _now()
    if note:
        task.setdefault("notes", []).append({"ts": _now(), "note": note})
    queue_event("status", task["id"], task.get("agent"),
                f"{old} -> {new}" + (f": {note}" if note else ""))


def unmet_dependencies(state: dict, task: dict) -> list[str]:
    unmet = []
    for dep in task.get("dependencies", []):
        try:
            d = get_task(state, dep)
        except Refused:
            unmet.append(f"{dep} (does not exist)")
            continue
        if d["status"] not in SATISFIED:
            unmet.append(f"{dep} ({d['status']})")
    return unmet


def active_count(state: dict, exclude: str | None = None) -> int:
    return sum(1 for t in state["tasks"]
               if t["status"] in ACTIVE_WORK and t["id"] != exclude)


REQUIRED_TASK_KEYS = ("id", "title", "status")


def validate_tasks(state: dict) -> None:
    """Fail loudly on a malformed record rather than with a KeyError traceback.

    A torn write can leave a task missing a field, and a stack trace is a worse
    signal than the repair instruction the corrupt-JSON path already gives.
    """
    for i, t in enumerate(state.get("tasks", [])):
        if not isinstance(t, dict):
            raise Refused(f"Task at index {i} is not an object. "
                          f"Repair {STATE_PATH} by hand or restore from git.")
        missing = [k for k in REQUIRED_TASK_KEYS if k not in t]
        if missing:
            raise Refused(
                f"Task at index {i} ({t.get('id', 'no id')}) is missing "
                f"{', '.join(missing)}. Repair {STATE_PATH} by hand or restore "
                "from git.")


def _dependency_cycles(state: dict) -> list[list[str]]:
    """Every dependency cycle, so the lead sees why a task can never start."""
    deps = {t["id"]: [d for d in t.get("dependencies", []) if d != t["id"]]
            for t in state["tasks"]}
    cycles: list[list[str]] = []
    seen: set[str] = set()

    def walk(node: str, trail: list[str]) -> None:
        if node in trail:
            cycle = trail[trail.index(node):] + [node]
            if not any(set(cycle) == set(c) for c in cycles):
                cycles.append(cycle)
            return
        if node in seen or node not in deps:
            return
        for nxt in deps[node]:
            walk(nxt, trail + [node])

    for task_id in deps:
        walk(task_id, [])
        seen.add(task_id)
    return cycles


# --- commands ----------------------------------------------------------------

def cmd_init(args) -> int:
    if STATE_PATH.exists() and not args.force:
        print(f"{STATE_PATH} already exists. Pass --force to reset it.")
        return 1
    state = default_state()
    state["objective"] = args.objective or ""
    state["sprint"] = args.sprint or ""
    queue_event("init", None, None, "state initialised")
    save_state(state)
    render(state)
    print(f"Initialised {STATE_PATH}")
    return 0


def cmd_add(args) -> int:
    state = load_state()
    if not TASK_ID_RE.match(args.id):
        raise Refused(f"Task id must look like PK-104, got {args.id!r}")
    if any(t["id"] == args.id for t in state["tasks"]):
        raise Refused(f"Task {args.id} already exists")
    if args.id in (args.depends or []):
        raise Refused(f"{args.id} cannot depend on itself: it could never "
                      "reach READY, and the board would show no reason why.")
    task = {
        "id": args.id,
        "title": args.title,
        "agent": args.agent,
        "status": "BACKLOG",
        "dependencies": args.depends or [],
        "owns": [normalize_path(p) for p in (args.own or [])],
        "branch": None,
        "worktree": None,
        "acceptance": args.acceptance or [],
        "tests": {"required": args.test or [], "ci_run": None},
        "pr": None,
        "review": None,
        "blocked_by": None,
        "created": _now(),
        "updated": _now(),
        "notes": [],
    }
    state["tasks"].append(task)
    queue_event("add", task["id"], task["agent"], task["title"])
    save_state(state)
    render(state)
    print(f"{args.id} added to BACKLOG"
          + (f", owner {args.agent}" if args.agent else ", unowned"))
    return 0


def cmd_ready(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    unmet = unmet_dependencies(state, task)
    if unmet and not args.force:
        raise Refused(f"{args.id} has unmet dependencies: {', '.join(unmet)}. "
                      "A task is READY only when every dependency is merged.")
    if not task.get("agent") and not args.force:
        raise Refused(f"{args.id} has no owner agent. Set one with "
                      f"`agentctl reassign {args.id} --agent <name>` first.")
    set_status(state, task, "READY")
    save_state(state)
    render(state)
    print(f"{args.id} -> READY")
    return 0


def cmd_assign(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    if args.agent:
        task["agent"] = args.agent
    if not task.get("agent"):
        raise Refused(f"{args.id} needs an owner agent before assignment")

    paths = [normalize_path(p) for p in (args.own or [])] or task.get("owns", [])
    if not paths and not args.force:
        raise Refused(f"{args.id}: declare the files or components this task "
                      "will touch with --own. An unbounded claim cannot be "
                      "collision-checked.")
    collisions = find_collisions(state, args.id, paths)
    if collisions:
        lines = [f"  {ours}  collides with  {theirs}  held by {other}"
                 for other, theirs, ours in collisions]
        raise Refused(f"{args.id}: ownership collision, assignment refused.\n"
                      + "\n".join(lines)
                      + "\nSequence the tasks, split at the component boundary, "
                        "or give one task both paths.")
    task["owns"] = paths
    task["branch"] = (args.branch or task.get("branch")
                      or f"agent/{task['agent']}/{task['id']}")
    if args.worktree:
        task["worktree"] = args.worktree
    set_status(state, task, "ASSIGNED", note=f"claimed {len(paths)} path(s)",
               force=args.force)
    save_state(state)
    render(state)
    print(f"{args.id} -> ASSIGNED to {task['agent']} on {task['branch']}")
    for p in paths:
        print(f"  owns {p}")
    return 0


def cmd_start(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    set_status(state, task, "IN_PROGRESS")
    save_state(state)
    render(state)
    print(f"{args.id} -> IN_PROGRESS")
    return 0


def cmd_review(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    if not args.pr:
        raise Refused(f"{args.id}: --pr is required. Review starts from a "
                      "pushed branch and an open PR, not from a claim of "
                      "doneness.")
    task["pr"] = args.pr
    set_status(state, task, "REVIEW", note=f"PR #{args.pr}")
    save_state(state)
    render(state)
    print(f"{args.id} -> REVIEW on PR #{args.pr}")
    return 0


def cmd_qa(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    if args.verdict not in REVIEW_VERDICTS:
        raise Refused(f"Review verdict must be one of {sorted(REVIEW_VERDICTS)}")
    task["review"] = {"verdict": args.verdict, "by": args.by or "code-reviewer",
                      "notes": args.notes or "", "ts": _now()}
    if args.verdict == "reject":
        set_status(state, task, "REWORK_REQUIRED",
                   note=f"review rejected: {args.notes or ''}",
                   force=args.force)
        save_state(state)
        render(state)
        print(f"{args.id} -> REWORK_REQUIRED (review rejected)")
        return 0
    set_status(state, task, "QA", note=f"review {args.verdict}")
    save_state(state)
    render(state)
    print(f"{args.id} -> QA (review {args.verdict})")
    return 0


def cmd_approve(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    if args.force:
        # A forced approval must stay visible forever. Without this the record
        # is indistinguishable from a real one at audit time, which makes the
        # gate decorative.
        if not args.reason:
            raise Refused(f"{args.id}: --force on approve requires --reason. "
                          "A bypassed gate has to say why, permanently.")
        task["tests"]["ci_run"] = args.ci_run
        task["tests"]["forced"] = {"reason": args.reason, "ts": _now()}
        set_status(state, task, "APPROVED",
                   note=f"APPROVAL FORCED without a verified CI run: {args.reason}")
        save_state(state)
        render(state)
        print(f"{args.id} -> APPROVED (FORCED: {args.reason})")
        return 0

    if not args.ci_run:
        raise Refused(f"{args.id}: --ci-run is required to leave QA. A green "
                      "CI run id is the evidence; an agent reporting that "
                      "tests pass is not.")
    # GitHub run ids are numeric. This catches `--ci-run pass`, which would
    # otherwise satisfy the gate with a word.
    if not args.ci_run.isdigit():
        raise Refused(f"{args.id}: {args.ci_run!r} is not a CI run id. Use the "
                      "numeric id from `gh run list --branch "
                      f"{task.get('branch') or '<branch>'}`, or --force with "
                      "--reason if there is genuinely no run.")
    task["tests"]["ci_run"] = args.ci_run
    task["tests"].pop("forced", None)
    set_status(state, task, "APPROVED", note=f"CI run {args.ci_run}")
    save_state(state)
    render(state)
    print(f"{args.id} -> APPROVED (CI run {args.ci_run})")
    return 0


def cmd_merged(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    if not args.human_approved:
        raise Refused(
            f"{args.id}: merge requires --human-approved. No agent merges to "
            "main on its own authority. Confirm with the product owner, then "
            "rerun with the flag.")
    # Persist the approval, not just the check. "Human in the loop AND an audit
    # trail" is the house rule, and a merge that skipped the gate by hand-
    # editing the JSON must not look identical to one that did not.
    task["merge_commit"] = args.commit
    task["human_approval"] = {"approved": True,
                              "approver": args.approver or "product owner",
                              "ts": _now()}
    set_status(state, task, "MERGED",
               note=(f"merged as {args.commit or 'unknown commit'}, "
                     f"human-approved by {task['human_approval']['approver']}"))
    save_state(state)
    render(state)
    print(f"{args.id} -> MERGED (approved by "
          f"{task['human_approval']['approver']})")
    return 0


def cmd_done(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    set_status(state, task, "DONE")
    task["owns"] = []          # release the claim so successors can proceed
    save_state(state)
    render(state)
    print(f"{args.id} -> DONE, ownership released")
    return 0


def cmd_block(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    task["blocked_by"] = args.reason
    set_status(state, task, "BLOCKED", note=args.reason)
    save_state(state)
    render(state)
    print(f"{args.id} -> BLOCKED: {args.reason}")
    return 0


def cmd_unblock(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    task["blocked_by"] = None
    set_status(state, task, args.to, note="unblocked", force=args.force)
    save_state(state)
    render(state)
    print(f"{args.id} -> {args.to}")
    return 0


def cmd_fail(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    set_status(state, task, "FAILED", note=args.reason)
    task["owns"] = []
    save_state(state)
    render(state)
    print(f"{args.id} -> FAILED: {args.reason}. Reassign with ready/assign.")
    return 0


def cmd_rework(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    set_status(state, task, "REWORK_REQUIRED", note=args.reason,
               force=args.force)
    save_state(state)
    render(state)
    print(f"{args.id} -> REWORK_REQUIRED: {args.reason}")
    return 0


def cmd_reassign(args) -> int:
    state = load_state()
    task = get_task(state, args.id)
    old = task.get("agent")
    task["agent"] = args.agent
    task["updated"] = _now()
    queue_event("reassign", task["id"], args.agent, f"from {old}")
    save_state(state)
    render(state)
    print(f"{args.id} reassigned: {old} -> {args.agent}")
    return 0


def cmd_check(args) -> int:
    """Validate the invariants. Exit 1 on any violation."""
    state = load_state()
    problems: list[str] = []
    seen: set[str] = set()
    for t in state["tasks"]:
        if t["id"] in seen:
            problems.append(f"duplicate task id {t['id']}")
        seen.add(t["id"])
        if t["status"] not in STATUSES:
            problems.append(f"{t['id']}: unknown status {t['status']}")
        for dep in t.get("dependencies", []):
            if dep == t["id"]:
                problems.append(f"{t['id']} depends on itself, so it can never "
                                "reach READY")
            elif not any(o["id"] == dep for o in state["tasks"]):
                problems.append(f"{t['id']}: dependency {dep} does not exist")
        # A gate that was forced, or a merge with no recorded approval, has to
        # stay visible at audit time.
        if t.get("tests", {}).get("forced"):
            problems.append(f"{t['id']}: approved on a FORCED gate, reason: "
                            f"{t['tests']['forced'].get('reason')}")
        if t["status"] in {"APPROVED", "MERGED", "DONE"} \
                and not t.get("tests", {}).get("ci_run"):
            problems.append(f"{t['id']} is {t['status']} with no CI run id")
        if t["status"] in {"MERGED", "DONE"} and not t.get("human_approval"):
            problems.append(f"{t['id']} is {t['status']} with no recorded human "
                            "approval, which means the status was set outside "
                            "agentctl")
        if t["status"] in CLAIMING - {"BLOCKED"}:
            unmet = unmet_dependencies(state, t)
            if unmet:
                problems.append(f"{t['id']} is {t['status']} with unmet "
                                f"dependencies: {', '.join(unmet)}")
    for t in state["tasks"]:
        if t["status"] not in CLAIMING:
            continue
        for other, theirs, ours in find_collisions(state, t["id"],
                                                   t.get("owns", [])):
            if t["id"] < other:
                problems.append(
                    f"ownership collision: {t['id']} {ours} vs {other} {theirs}")
    cap = state["config"]["max_concurrent"]
    if active_count(state) > cap:
        problems.append(f"{active_count(state)} tasks in active work, cap is {cap}")
    for cycle in _dependency_cycles(state):
        problems.append("dependency cycle, none of these can ever start: "
                        + " -> ".join(cycle))
    if problems:
        print("FAIL")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"OK: {len(state['tasks'])} task(s), {active_count(state)}/{cap} "
          "active, no collisions, no unmet dependencies on live work.")
    return 0


def cmd_status(args) -> int:
    state = load_state()
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0
    if args.id:
        print(_task_detail(get_task(state, args.id)))
        return 0
    print(_render_body(state))
    return 0


def cmd_log(args) -> int:
    if not LOG_PATH.exists():
        print("No activity yet.")
        return 0
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
    for line in lines[-args.n:]:
        # The log is the one file written non-atomically, in a repo whose
        # documented failure mode is a torn write. One bad line must not make
        # the entire history unreadable.
        try:
            row = json.loads(line)
            who = row.get("agent") or "-"
            print(f"{row['ts']}  {row.get('task') or '-':<8}  {who:<20}  "
                  f"{row['event']}: {row['detail']}")
        except (json.JSONDecodeError, KeyError):
            print(f"<unparseable log line> {line[:120]}")
    return 0


def cmd_render(args) -> int:
    render(load_state())
    print(f"Rendered {RENDER_PATH}")
    return 0


# --- rendering ---------------------------------------------------------------

def _task_detail(t: dict) -> str:
    lines = [
        f"{t['id']}  {t['title']}",
        f"  status       {t['status']}",
        f"  agent        {t.get('agent') or '-'}",
        f"  branch       {t.get('branch') or '-'}",
        f"  worktree     {t.get('worktree') or '-'}",
        f"  depends on   {', '.join(t.get('dependencies') or []) or '-'}",
        f"  owns         {', '.join(t.get('owns') or []) or '-'}",
        f"  PR           {('#' + str(t['pr'])) if t.get('pr') else '-'}",
        f"  CI run       {t.get('tests', {}).get('ci_run') or '-'}",
        f"  review       {(t.get('review') or {}).get('verdict', '-')}",
        f"  blocked by   {t.get('blocked_by') or '-'}",
    ]
    if t.get("acceptance"):
        lines.append("  acceptance")
        lines += [f"    - {a}" for a in t["acceptance"]]
    return "\n".join(lines)


ORDER = ["IN_PROGRESS", "REWORK_REQUIRED", "ASSIGNED", "REVIEW", "QA",
         "APPROVED", "BLOCKED", "READY", "BACKLOG", "FAILED", "MERGED", "DONE"]


def _render_body(state: dict) -> str:
    cap = state["config"]["max_concurrent"]
    out = [f"Objective: {state.get('objective') or '(none set)'}",
           f"Sprint: {state.get('sprint') or '(none set)'}",
           f"Active work: {active_count(state)}/{cap}",
           f"Updated: {state.get('updated')}",
           ""]
    by_status: dict[str, list[dict]] = {}
    for t in state["tasks"]:
        by_status.setdefault(t["status"], []).append(t)
    for status in ORDER:
        rows = by_status.get(status)
        if not rows:
            continue
        out.append(f"## {status}")
        for t in sorted(rows, key=lambda x: x["id"]):
            tail = []
            if t.get("agent"):
                tail.append(t["agent"])
            if t.get("pr"):
                tail.append(f"PR #{t['pr']}")
            if t.get("blocked_by"):
                tail.append(f"blocked: {t['blocked_by']}")
            if t.get("dependencies"):
                tail.append("deps " + ",".join(t["dependencies"]))
            out.append(f"- **{t['id']}** {t['title']}"
                       + (f"  ({', '.join(tail)})" if tail else ""))
            if t.get("owns"):
                out.append(f"  - owns: {', '.join(t['owns'])}")
        out.append("")
    if not state["tasks"]:
        out.append("No tasks yet.")
    return "\n".join(out).rstrip() + "\n"


def render(state: dict) -> None:
    header = (
        "# Pricekeel project state\n\n"
        "> Generated by `python tools/agentctl.py render`. Do not hand-edit:\n"
        "> `docs/agents/project_state.json` is authoritative and every change\n"
        "> to it goes through `tools/agentctl.py`.\n\n"
    )
    _atomic_write(RENDER_PATH, header + _render_body(state))


# --- CLI ---------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agentctl",
        description="Task state machine for the Pricekeel agent engineering org.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create the state file")
    s.add_argument("--objective", default="")
    s.add_argument("--sprint", default="")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("add", help="create a task in BACKLOG")
    s.add_argument("id")
    s.add_argument("title")
    s.add_argument("--agent")
    s.add_argument("--depends", action="append")
    s.add_argument("--own", action="append")
    s.add_argument("--acceptance", action="append")
    s.add_argument("--test", action="append")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("ready", help="BACKLOG -> READY (dependencies must be merged)")
    s.add_argument("id")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_ready)

    s = sub.add_parser("assign", help="READY -> ASSIGNED, claims files")
    s.add_argument("id")
    s.add_argument("--agent")
    s.add_argument("--branch")
    s.add_argument("--worktree")
    s.add_argument("--own", action="append")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_assign)

    s = sub.add_parser("start", help="ASSIGNED -> IN_PROGRESS")
    s.add_argument("id")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("review", help="IN_PROGRESS -> REVIEW (needs a PR)")
    s.add_argument("id")
    s.add_argument("--pr", type=int)
    s.set_defaults(func=cmd_review)

    s = sub.add_parser("qa", help="REVIEW -> QA, or REWORK_REQUIRED on reject")
    s.add_argument("id")
    s.add_argument("--verdict", required=True)
    s.add_argument("--by")
    s.add_argument("--notes")
    s.add_argument("--force", action="store_true",
                   help="bypass the concurrency cap when a reject sends a "
                        "task back into active work")
    s.set_defaults(func=cmd_qa)

    s = sub.add_parser("approve", help="QA -> APPROVED (needs a green CI run id)")
    s.add_argument("id")
    s.add_argument("--ci-run", dest="ci_run")
    s.add_argument("--force", action="store_true",
                   help="approve without a verified CI run; requires --reason "
                        "and is recorded permanently")
    s.add_argument("--reason", help="why the gate was forced")
    s.set_defaults(func=cmd_approve)

    s = sub.add_parser("merged", help="APPROVED -> MERGED (needs --human-approved)")
    s.add_argument("id")
    s.add_argument("--commit")
    s.add_argument("--approver", help="who approved the merge")
    s.add_argument("--human-approved", dest="human_approved", action="store_true")
    s.set_defaults(func=cmd_merged)

    s = sub.add_parser("done", help="MERGED -> DONE, releases ownership")
    s.add_argument("id")
    s.set_defaults(func=cmd_done)

    s = sub.add_parser("block", help="move to BLOCKED")
    s.add_argument("id")
    s.add_argument("--reason", required=True)
    s.set_defaults(func=cmd_block)

    s = sub.add_parser("unblock", help="BLOCKED -> a live status")
    s.add_argument("id")
    s.add_argument("--to", default="IN_PROGRESS")
    s.add_argument("--force", action="store_true",
                   help="bypass the concurrency cap")
    s.set_defaults(func=cmd_unblock)

    s = sub.add_parser("fail", help="move to FAILED, releases ownership")
    s.add_argument("id")
    s.add_argument("--reason", required=True)
    s.set_defaults(func=cmd_fail)

    s = sub.add_parser("rework", help="move to REWORK_REQUIRED")
    s.add_argument("id")
    s.add_argument("--reason", required=True)
    s.add_argument("--force", action="store_true",
                   help="bypass the concurrency cap")
    s.set_defaults(func=cmd_rework)

    s = sub.add_parser("reassign", help="change the owner agent")
    s.add_argument("id")
    s.add_argument("--agent", required=True)
    s.set_defaults(func=cmd_reassign)

    s = sub.add_parser("check", help="validate every invariant")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("status", help="show the board or one task")
    s.add_argument("--id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("log", help="tail the activity log")
    s.add_argument("-n", type=int, default=30)
    s.set_defaults(func=cmd_log)

    s = sub.add_parser("render", help="regenerate PROJECT_STATE.md")
    s.set_defaults(func=cmd_render)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
