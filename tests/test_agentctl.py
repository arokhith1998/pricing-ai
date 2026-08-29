"""Known-answer tests for the agent task state machine.

This is the trust-critical part of the multi-agent workflow, in the same sense
that `pricing/metrics.py` is the trust-critical part of the product: if the
transition table, the ownership check, or the merge gate is wrong, two agents
overwrite each other's work or unreviewed code reaches main. Both failures are
silent, so they get tests.
"""

from __future__ import annotations

import json

import pytest

from tools import agentctl


@pytest.fixture
def ctl(tmp_path, monkeypatch):
    """Point the module at a throwaway state dir so tests never touch docs/."""
    monkeypatch.setattr(agentctl, "AGENT_DIR", tmp_path)
    monkeypatch.setattr(agentctl, "STATE_PATH", tmp_path / "project_state.json")
    monkeypatch.setattr(agentctl, "LOG_PATH", tmp_path / "activity.jsonl")
    monkeypatch.setattr(agentctl, "RENDER_PATH", tmp_path / "PROJECT_STATE.md")
    return agentctl


def run(argv: list[str]) -> int:
    return agentctl.main(argv)


def add_task(task_id: str, *, agent: str = "backend-engineer",
             owns: list[str] | None = None,
             depends: list[str] | None = None) -> None:
    argv = ["add", task_id, f"title {task_id}", "--agent", agent]
    for p in owns or []:
        argv += ["--own", p]
    for d in depends or []:
        argv += ["--depends", d]
    assert run(argv) == 0


# --- ownership arithmetic ----------------------------------------------------

@pytest.mark.parametrize("a,b,expected", [
    # Same file, whole-file claims.
    ("api/main.py", "api/main.py", True),
    # Distinct components of the same file are the whole point of component
    # ownership: api/main.py carries six unrelated route groups.
    ("api/main.py#crm", "api/main.py#copilot", False),
    ("api/main.py#crm", "api/main.py#crm", True),
    # A whole-file claim swallows every component of that file.
    ("api/main.py", "api/main.py#crm", True),
    ("api/main.py#crm", "api/main.py", True),
    # Directory containment.
    ("web", "web/src/app/page.tsx", True),
    ("web/src", "web/src/components/Nav.tsx", True),
    # Sibling paths do not conflict.
    ("pricing/metrics.py", "pricing/model.py", False),
    ("web/src", "web/test", False),
    # Prefix that is not a path-segment boundary must not conflict.
    ("web/src", "web/src-legacy/x.ts", False),
])
def test_paths_conflict(a, b, expected):
    assert agentctl.paths_conflict(a, b) is expected
    assert agentctl.paths_conflict(b, a) is expected


@pytest.mark.parametrize("raw,expected", [
    ("./pricing/metrics.py", "pricing/metrics.py"),
    ("pricing\\metrics.py", "pricing/metrics.py"),
    ("web/", "web"),
    ("  api/main.py#crm  ", "api/main.py#crm"),
])
def test_normalize_path(raw, expected):
    assert agentctl.normalize_path(raw) == expected


def test_normalize_path_rejects_empty():
    with pytest.raises(agentctl.Refused):
        agentctl.normalize_path("#crm")


# --- transitions -------------------------------------------------------------

def test_happy_path_reaches_done(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    assert run(["ready", "PK-1"]) == 0
    assert run(["assign", "PK-1"]) == 0
    assert run(["start", "PK-1"]) == 0
    assert run(["review", "PK-1", "--pr", "99"]) == 0
    assert run(["qa", "PK-1", "--verdict", "approve"]) == 0
    assert run(["approve", "PK-1", "--ci-run", "12345"]) == 0
    assert run(["merged", "PK-1", "--commit", "abc1234",
                "--human-approved"]) == 0
    assert run(["done", "PK-1"]) == 0

    task = agentctl.get_task(agentctl.load_state(), "PK-1")
    assert task["status"] == "DONE"
    assert task["pr"] == 99
    assert task["tests"]["ci_run"] == "12345"
    assert task["merge_commit"] == "abc1234"
    # DONE releases the claim so a dependent task can take the same files.
    assert task["owns"] == []


def test_illegal_transition_is_refused(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    # BACKLOG straight to IN_PROGRESS skips assignment and the collision check.
    assert run(["start", "PK-1"]) == 1
    assert agentctl.get_task(agentctl.load_state(), "PK-1")["status"] == "BACKLOG"


def test_terminal_done_accepts_nothing(ctl):
    assert agentctl.TRANSITIONS["DONE"] == set()


def test_every_transition_target_is_a_known_status():
    for source, targets in agentctl.TRANSITIONS.items():
        assert source in agentctl.STATUSES
        for t in targets:
            assert t in agentctl.STATUSES, f"{source} -> {t} is not a status"


# --- the gates ---------------------------------------------------------------

def test_merge_requires_human_approval(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "99"])
    run(["qa", "PK-1", "--verdict", "approve"])
    run(["approve", "PK-1", "--ci-run", "12345"])

    assert run(["merged", "PK-1", "--commit", "abc"]) == 1
    assert agentctl.get_task(agentctl.load_state(), "PK-1")["status"] == "APPROVED"


def test_approve_requires_a_ci_run_id(ctl):
    """An agent's word that tests pass is not evidence. A run id is."""
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "99"])
    run(["qa", "PK-1", "--verdict", "approve"])

    assert run(["approve", "PK-1"]) == 1
    assert agentctl.get_task(agentctl.load_state(), "PK-1")["status"] == "QA"


def test_review_requires_a_pr(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["start", "PK-1"])

    assert run(["review", "PK-1"]) == 1
    assert agentctl.get_task(agentctl.load_state(),
                             "PK-1")["status"] == "IN_PROGRESS"


def test_rejected_review_sends_the_task_back(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "99"])

    assert run(["qa", "PK-1", "--verdict", "reject", "--notes", "no tests"]) == 0
    task = agentctl.get_task(agentctl.load_state(), "PK-1")
    assert task["status"] == "REWORK_REQUIRED"
    assert task["review"]["verdict"] == "reject"
    # Rework returns to the coding agent, not to QA.
    assert run(["start", "PK-1"]) == 0


def test_unknown_review_verdict_is_refused(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "99"])
    assert run(["qa", "PK-1", "--verdict", "lgtm"]) == 1


# --- dependencies ------------------------------------------------------------

def test_ready_is_refused_while_a_dependency_is_open(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    add_task("PK-2", owns=["api/main.py#crm"], depends=["PK-1"])

    assert run(["ready", "PK-2"]) == 1
    assert agentctl.get_task(agentctl.load_state(), "PK-2")["status"] == "BACKLOG"


def test_ready_allowed_once_the_dependency_is_merged(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    add_task("PK-2", owns=["api/main.py#crm"], depends=["PK-1"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "1"])
    run(["qa", "PK-1", "--verdict", "approve"])
    run(["approve", "PK-1", "--ci-run", "1"])
    run(["merged", "PK-1", "--human-approved"])

    assert run(["ready", "PK-2"]) == 0


def test_missing_dependency_is_reported(ctl):
    add_task("PK-2", owns=["api/main.py"], depends=["PK-404"])
    assert run(["ready", "PK-2"]) == 1


# --- collision prevention ----------------------------------------------------

def test_overlapping_claim_is_refused(ctl):
    """The whole reason this tool exists. Two agents, one file, no silent loss."""
    add_task("PK-1", agent="backend-engineer", owns=["api/main.py"])
    add_task("PK-2", agent="ai-engineer", owns=["api/main.py#copilot"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])

    run(["ready", "PK-2"])
    assert run(["assign", "PK-2"]) == 1
    assert agentctl.get_task(agentctl.load_state(), "PK-2")["status"] == "READY"


def test_disjoint_components_of_one_file_can_run_together(ctl):
    add_task("PK-1", agent="backend-engineer", owns=["api/main.py#crm"])
    add_task("PK-2", agent="ai-engineer", owns=["api/main.py#copilot"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["ready", "PK-2"])
    assert run(["assign", "PK-2"]) == 0


def test_claim_released_by_done_frees_the_path(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    add_task("PK-2", agent="qa-engineer", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["ready", "PK-2"])
    assert run(["assign", "PK-2"]) == 1

    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "1"])
    run(["qa", "PK-1", "--verdict", "approve"])
    run(["approve", "PK-1", "--ci-run", "1"])
    run(["merged", "PK-1", "--human-approved"])
    run(["done", "PK-1"])

    assert run(["assign", "PK-2"]) == 0


def test_failed_task_releases_its_claim(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    add_task("PK-2", agent="qa-engineer", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["fail", "PK-1", "--reason", "hallucinated a module"])

    run(["ready", "PK-2"])
    assert run(["assign", "PK-2"]) == 0


def test_assignment_without_a_declared_scope_is_refused(ctl):
    add_task("PK-1")
    run(["ready", "PK-1"])
    assert run(["assign", "PK-1"]) == 1


# --- concurrency cap ---------------------------------------------------------

def test_concurrency_cap_blocks_a_third_active_task(ctl):
    """Two coding agents at once is the proven-safe ceiling on one checkout."""
    for i, path in enumerate(["pricing/metrics.py", "web/src", "neon"], start=1):
        add_task(f"PK-{i}", owns=[path])
        run(["ready", f"PK-{i}"])
    assert run(["assign", "PK-1"]) == 0
    assert run(["assign", "PK-2"]) == 0
    assert run(["assign", "PK-3"]) == 1

    # Review does not count as active work: the agent has stopped editing.
    run(["start", "PK-1"])
    run(["review", "PK-1", "--pr", "1"])
    assert run(["assign", "PK-3"]) == 0


# --- integrity ---------------------------------------------------------------

def test_check_passes_on_a_clean_board(ctl, capsys):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    assert run(["check"]) == 0
    assert "OK:" in capsys.readouterr().out


def test_check_catches_a_hand_edited_collision(ctl, capsys):
    """The state file is only authoritative if tampering is detectable."""
    add_task("PK-1", owns=["api/main.py"])
    add_task("PK-2", agent="ai-engineer", owns=["api/main.py#copilot"])
    state = agentctl.load_state()
    for t in state["tasks"]:
        t["status"] = "IN_PROGRESS"
    agentctl.save_state(state)

    assert run(["check"]) == 1
    assert "ownership collision" in capsys.readouterr().out


def test_duplicate_task_id_is_refused(ctl):
    add_task("PK-1", owns=["pricing/metrics.py"])
    assert run(["add", "PK-1", "again", "--agent", "backend-engineer"]) == 1


def test_bad_task_id_shape_is_refused(ctl):
    assert run(["add", "TASK-1", "nope", "--agent", "backend-engineer"]) == 1


def test_corrupt_state_file_refuses_rather_than_resetting(ctl, tmp_path):
    """Torn writes have truncated files in this repo. Never silently start over."""
    (tmp_path / "project_state.json").write_text("{ not json", encoding="utf-8")
    assert run(["status"]) == 1


def test_state_write_is_atomic_and_leaves_no_temp_files(ctl, tmp_path):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert json.loads((tmp_path / "project_state.json").read_text(
        encoding="utf-8"))["tasks"][0]["status"] == "READY"


# --- observability -----------------------------------------------------------

def test_every_mutation_lands_in_the_activity_log(ctl, tmp_path):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["block", "PK-1", "--reason", "waiting on a schema decision"])

    rows = [json.loads(line) for line
            in (tmp_path / "activity.jsonl").read_text(encoding="utf-8").splitlines()]
    events = [r["event"] for r in rows]
    assert events.count("add") == 1
    assert events.count("status") == 3
    assert all(r["task"] == "PK-1" for r in rows)
    assert "waiting on a schema decision" in rows[-1]["detail"]


def test_blocked_task_reports_why(ctl, capsys):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["ready", "PK-1"])
    run(["assign", "PK-1"])
    run(["block", "PK-1", "--reason", "needs the neon migration first"])
    capsys.readouterr()

    run(["status", "--id", "PK-1"])
    out = capsys.readouterr().out
    assert "BLOCKED" in out
    assert "needs the neon migration first" in out


def test_render_marks_the_file_as_generated(ctl, tmp_path):
    add_task("PK-1", owns=["pricing/metrics.py"])
    run(["render"])
    text = (tmp_path / "PROJECT_STATE.md").read_text(encoding="utf-8")
    assert "Do not hand-edit" in text
    assert "PK-1" in text
