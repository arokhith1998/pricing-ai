# Graph dev workflow

How we make changes to Pricekeel. Replaces ad-hoc single-prompt requests with an
explicit graph of specialized nodes, adversarial checks, and human gates.

This is about **how we build the tool**, not about the tool's architecture. Nothing here
proposes putting a graph framework inside `pricing/`. See "Level 3" at the bottom for when
that would be justified.

## Why

On 2026-08-22 an external assistant was given `CLAUDE.md` and asked for a build plan. The
file still said "product code does not exist yet" and "not yet a git repo", both true on
2026-05-26 and false ever since. Eleven steps came back. Scored against the repo:

| Outcome | Steps |
|---|---|
| Correct | 2 |
| Correct but incomplete | 1 |
| Already shipped, would have rebuilt working code | 5 |
| Actively destructive or a regression | 3 |

Every failure traced to **one unverified premise**. Not to a weak model, a vague prompt,
or a missing framework. The fix is not a better prompt. It is a node whose only job is to
check premises before anything downstream runs.

That is the whole argument for graph engineering here: a single pass asks one model to
plan, research, implement, and grade itself. Splitting those roles and inserting a
verifier and an adversary is what turns a confident answer into a trustworthy one.

## The standard change graph

```
  [Request]
      |
      v
  [1 GROUND] ---- STOP ----> back to human, premises are wrong
      |
      | PROCEED / PROCEED WITH CORRECTIONS
      v
  [2 PLAN] (design doc for non-trivial work)
      |
      v
  [3 REVIEW]  parallel, only the nodes the routing table selects
      |
      +---> cto ................ architecture, data, security
      +---> cfo ................ unit economics, any money claim
      +---> pricing-strategist . framework grounding, methodology
      +---> market-sizing ...... any market number
      |
      v
  [4 SKEPTIC] ---- BLOCKING ----> back to [2 PLAN]
      |
      | NON-BLOCKING / CLEAN
      v
  [5 HUMAN GATE]  <-- you approve. Nothing irreversible happens before this.
      |
      v
  [6 IMPLEMENT]   backend-engineer | web-engineer
      |
      v
  [7 TEST] ---- red ----> back to [6 IMPLEMENT]
      |
      | green
      v
  [8 COMMIT + PUSH]  (standing rule: commit on every green run)
      |
      v
  [9 DECISION RECORD]  vault/Decisions/YYYY-MM-DD-<slug>.md
```

## Node catalog

| Node | Agent | Role |
|---|---|---|
| 1 Ground | `ground` | Verifies every premise. Read-only. Emits PROCEED / PROCEED WITH CORRECTIONS / STOP. |
| 2 Plan | main session or `Plan` | Design doc before non-trivial builds (working agreement #3). |
| 3 Review | `cto`, `cfo`, `pricing-strategist`, `market-sizing-analyst` | Domain critique, run in parallel. |
| 4 Skeptic | `skeptic` | Attacks the findings. Emits BLOCKING / NON-BLOCKING / CLEAN. |
| 5 Human gate | you | The only node that can authorize something irreversible. |
| 6 Implement | `backend-engineer`, `web-engineer` | The only nodes that write code. |
| 7 Test | `pytest`, `npm test` | Deterministic. Not a judgment call. |
| 8 Commit | implementer | Commit on green, keep branches pushed. |
| 9 Record | `obsidian-adr` skill | Decision record in the vault. |

## Routing

Do not run every node on every change. Ceremony that does not earn its cost gets skipped,
and a workflow nobody follows is worse than no workflow.

| Change type | Nodes |
|---|---|
| Typo, copy tweak, comment | 6, 7, 8. Skip the rest. |
| Bug fix with a failing test | 1, 6, 7, 8 |
| New engine capability | 1, 2, 3 (cto + pricing-strategist), 4, 5, 6, 7, 8, 9 |
| Schema or data-model change | 1, 2, 3 (cto), 4, 5, 6, 7, 8, 9 |
| Anything touching customer data flow | 1, 2, 3 (cto), 4, **5 mandatory**, 6, 7, 8, 9 |
| Pricing, packaging, or a money claim | 1, 3 (cfo + pricing-strategist), 4, 5, 9 |
| Marketing or landing copy | 1, 3 (pricing-strategist), 4, 5, 6, 7, 8 |
| Market sizing, deck, investor material | 1, 3 (market-sizing + cfo), 4, **5 mandatory**, 9 |
| **Any externally supplied plan** | **1 first, always.** Then route by type. |

That last row is the one that matters. Any plan you did not write, from any assistant,
any consultant, any blog post, enters at Ground.

## State and the paper trail

Level 2 of the maturity ladder: file-based state, no framework.

- **Intermediate node output** (ground report, review notes, skeptic objections) is
  scratch. It lives in the session scratchpad. It does not enter the repo.
- **The plan** for non-trivial work is a design doc under `docs/design/`.
- **The outcome** is a decision record in `vault/Decisions/YYYY-MM-DD-<slug>.md`, using
  the existing vault frontmatter schema. This is the durable artifact.
- **The code** is the commit. The commit message states what was verified and what the
  tests reported.

We deliberately do not invent a new `docs/graph-runs/` directory. The vault already has
`Decisions/` and `Logs/`, and the repo already has `docs/design/`. Reuse beats invention.

## Gates

Two things never happen without explicit human approval, regardless of routing:

1. **Irreversible or outward-facing actions.** Merges to main, force pushes, deploys,
   schema migrations against production, anything sent to a customer or published.
2. **Anything crossing the data boundary.** Row-level customer data reaching a model
   provider, a new subprocessor, a change to what `/trust` or `/privacy` claims.

## When NOT to use this

- Reading, exploring, answering a question. No graph. Just answer.
- One-line fixes. Routing overhead exceeds the work.
- When you already know the answer and can verify it in one command. Run the command.

The failure mode of graph engineering is five nodes confidently agreeing on the same
wrong premise, at five times the cost. Ground is what prevents that, which is why it is
first and why it is read-only.

## Level 3: when a framework would be justified

LangGraph is **proposed, not adopted**. It appears in no dependency file. It would be
justified for a **product** pipeline that is long-running, needs checkpoint and resume,
and is failure-tolerant: `pricing/ingest.py` and `pricing/matching.py` are the honest
candidates, where a partial failure should resume rather than restart.

It is **not** justified for `pricing/governance.py` or the number path in
`pricing/copilot.py`. Those are deliberately LLM-free and deterministic. The correlational
caveat there is a guarantee. Routing it through a model turns a guarantee into a
probability, which is the wrong direction for a claim a CFO has to defend.

It is also not needed for *this* workflow. The Agent tooling already provides the
orchestration; what was missing was the graph shape, the verifier, and the adversary.
