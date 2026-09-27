# Pricekeel state audit, lead lens, 2026-09-26

## 1. Verdict

The task machine is internally consistent and the gates genuinely bit, but the org it
governs is not on the mainline and the checkout it governs from is stale. `agentctl check`
returns clean (16 tasks, 0/2 active, no collisions), and every merge commit the board
claims (8c52e7c, 95aa3d6, 885aa46, ee43a6f, ca47c67, a977dd0) is a verified ancestor of
`origin/main`. The board is honest about git. Git is not honest about the board: PR #62,
which carries the entire org, has been open since 2026-08-29, `origin/main` contains no
`docs/agents/`, no `tools/agentctl.py`, and no `pk-lead`, `qa-engineer`, `code-reviewer`,
`ai-engineer`, or `data-engineer` definition. Meanwhile the working branch is 6 commits
behind main, so this tree still holds the 1408-line pre-PK-1 `api/main.py` while main
holds `api/routers/*`. Zero active work for 11 days, four READY tasks untouched for 15.
The critical path to a paid pilot is not engineering: `docs/ops/funnel-tracker.csv` is
header only, so the real blocker is interviews, an NDA, and the data-readiness gates.

## 2. Top six findings

1. **CRITICAL. The agent org is unmerged.** PR #62 open 28 days; `git ls-tree origin/main
   docs/` shows design, guides, legal, ops, reviews and no `agents`. The governance that
   gated six merged PRs does not exist for anyone checking out main. It also carries 42
   files and 6065 insertions including the investor deck and Llama Ventures GTM. Split it:
   org files plus `agentctl` in one PR, merge that this week; deck and GTM in a second.

2. **HIGH. The lead plans against dead code.** This branch is 6 behind `origin/main`;
   `wc -l api/main.py` = 1408 here, `git show origin/main:api/main.py | wc -l` = 310. Any
   dispatch from this tree targets a file layout PK-1 already deleted. Rebase before the
   next assignment.

3. **HIGH. `OWNERSHIP.md:58-75` is stale.** The `api/main.py` (1408 lines) hot-file table
   and its six `#component` spans describe the pre-PK-1 monolith. The file itself predicted
   this: "PK-1 in the backlog splits this file into routers, which removes the need for most
   of this table." Replace the table with the router map.

4. **HIGH. Untracked agent work outside the machine.** Branch
   `agent/ai-engineer/fix-time-split-silent-failures` with live worktree
   `.claude/worktrees/fix-model-silent`, 4 commits from 2026-09-15, 19 files, 767 insertions
   into the model, guidance, and ChatPanel. No PK id, no board row, no PR, so no review, no
   CI gate, no claim. Give it a PK id and a PR, or delete branch and worktree.

5. **MEDIUM-HIGH. PK-4 never ran and the backlog of PRs aged.** Filed 2026-08-29, still
   BACKLOG. All of #36 #37 #38 #59 #60 #61 remain open; #36 and #37 date to 2026-06-10 and
   carry ingest silent-corruption fixes, which is precisely the reliability a first customer
   CSV needs. Triage or close each with a stated reason.

6. **MEDIUM. Missing ADR on a trust-critical model choice.** The PK-15 review explicitly
   required one ("ADR needed in DECISIONS.md (lead)"); `DECISIONS.md` holds ADR-001 to
   ADR-005, all about the org, none about the monotone constraint. Explainability over
   accuracy is the product thesis; write ADR-006 on why discount is constrained +1 and why
   AUC 0.640 to 0.619 is the right trade.

## 3. Three genuinely good things

- **The gates were real, not theater.** PK-5 was rejected twice, PK-11 rejected on a
  numeric blocker the reviewer reproduced (0.344 vs 0.318 disagreeing with the rounded
  tile), PK-1 closed six rework items. A rubber-stamp pipeline does not produce those notes.
- **Traction discipline.** `gtm/llama-ventures/traction-update.md` states "Intro calls only.
  No NDA, no data received, no commitment, no revenue," and `funnel-tracker.csv` is header
  only rather than padded. That is rare and worth protecting.
- **Honest platform limits.** ADR-005 (a tool list does not make an agent read-only) and
  `WORKFLOW.md:88-91` (main is not protected server-side, treat as a known weakness) name
  the weaknesses instead of claiming them solved.

On over-engineering: 960 lines of `agentctl` for a solo founder is near the ceiling but has
earned its keep. Build PK-3 (approve fetches CI itself), which removes real toil. Defer
PK-8 and PK-13, which are process about process.

Sprint objective: "prove it on a real task" is met, six tasks through the full lifecycle
with real rejections. "Stand up" is not met while the org lives only on PR #62. Call it 80
percent, closable in one merge.

## 4. Next two weeks toward a paid pilot

| # | Task | Owner | Acceptance |
|---|---|---|---|
| 1 | Rebase on origin/main, split and merge PR #62 | pk-lead plans, human merges | main contains `docs/agents/` and `tools/agentctl.py`; `agentctl check` green from a fresh main checkout; tree shows `api/routers/*` |
| 2 | Refresh OWNERSHIP.md to the router layout | pk-lead | no claim references a `api/main.py#component` span that no longer exists |
| 3 | PK-4: triage the seven open PRs | pk-lead | each of #36 #37 #38 #59 #60 #61 is closed with a reason or filed as a PK task with an owner |
| 4 | Resolve the orphan silent-failure branch | pk-lead, then ai-engineer | branch has a PK id, a PR, and a CI run, or branch and worktree are deleted |
| 5 | Ingest hardening from #36 and #37 | backend-engineer | a customer-shaped CSV with above-list and malformed rows produces a LoadReport naming every dropped or coerced row; nothing is silently lost |
| 6 | PK-16: copilot slice reference and non-additivity | backend-engineer | slice opportunities reconcile to the headline figure or carry the caveat; `tests/test_copilot.py` pins both |
| 7 | PK-6, then PK-12, then PK-14 as one web sequence | web-engineer | no customer-facing page names OpenAI; no asserted-not-computed claim remains; green npm test, eslint, tsc, build |
| 8 | Close the real-data readiness gates and log five interviews | cto and cfo advise, founder executes | legal entity, counsel, NDA template, cyber/E&O each recorded with a date in `docs/ops/`; `funnel-tracker.csv` holds five real rows and one scheduled data-readiness review |

Items 1 to 4 are lead work and can run while item 5 or 7 runs, cap 2. Items 5 and 6 both
touch `pricing/` but disjoint modules, so they parallelize; 6 and 7 do not, because PK-14
renders what PK-16 changes. Item 8 gates everything: without an NDA and the readiness
gates you cannot accept a CSV, and without a CSV there is no pilot to be paid for.

Inspected directly: `project_state.json`, `agentctl check` and `status`, all branches and
worktrees, `gh pr list --state all --limit 30`, merge-base of all six merge commits,
`origin/main` tree, line counts of `api/main.py` on both refs, every path in OWNERSHIP.md,
`funnel-tracker.csv`, `traction-update.md`, the board note. Assumed, not verified: that the
Llama Ventures conversations are still live, and that CI on main is currently green.
