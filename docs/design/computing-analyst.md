# Computing analyst - design document

Status: proposed, 2026-08-18. Owner: founding engineer. Not approved to build.
Extends the LLM boundary set in `pricing/assist.py` and `pricing/copilot.py`.
It does not authorize unrelated capability expansion, and it does not change
the product wedge.

## The problem

Open-ended questions cannot be answered today.

`pricing/rag.py:177` serializes the analysis dict to JSON, truncates it to
6,000 characters, and tells the model not to infer row-level data. The model
therefore sees a partial summary of pre-computed aggregates and nothing else.
Meanwhile the enriched frame is sitting in `analysis["data"]` and is never
queried.

Two consequences:

1. Any question outside the pre-built metric set in `pricing/metrics.py` is
   unanswerable. "What if we capped discounts at 15% for EMEA renewals only"
   requires a code change and a deploy.
2. The six canonical copilot questions are the ceiling of the conversation,
   not the floor.

The constraint that produced this is correct and stays. It was implemented as
"the model never touches data," which is stronger than the rule requires and
costs the product its analytical range.

## The distinction this document turns on

Two different things are routinely conflated as "letting the LLM compute."

**Model as calculator.** The model emits a number from its weights.
Non-reproducible across runs, unattributable, and indefensible in a pricing
committee. It also makes the immutable decision log worthless, because a log
entry whose number cannot be regenerated is a record of nothing. This stays
banned, permanently, and is not what this document proposes.

**Model as query author.** The model emits code, the engine executes it, and
the code ships with the answer. Deterministic on re-run, inspectable by the
buyer, and storable as provenance.

The governing rule becomes: **the model never states a number it did not
derive from executed code.** That is a strengthening of the current rule, not
a relaxation of it. Today the model narrates numbers it was handed. Under this
design it narrates numbers it can point at a query for.

## Design

Loop:

```
question
  -> model emits SQL against the canonical frame (sees schema, not data)
  -> validator accepts or rejects
  -> executor runs it read-only, timed, row-capped
  -> result + SQL returned
  -> model narrates the result only
```

### 1. Query surface: SQL, not Python

Recommend SQL over an in-memory read-only DuckDB view of the enriched frame,
rather than a sandboxed pandas subset.

Reasons: SQL parses cleanly so the validator is a real gate rather than a
regex; there is no `eval()` surface; and a RevOps or Finance buyer can read
the query, which is the entire point of showing it. A pandas expression shown
to a Head of Pricing is not evidence, it is noise.

Cost: a DuckDB dependency, and a mapping layer from the enriched frame to a
stable table definition.

### 2. Validation gate

Reject before execution, not after:

- `SELECT` only. No DDL, DML, `ATTACH`, `COPY`, `INSTALL`, `PRAGMA`, or any
  file-system function.
- Single allowed table, the canonical deal view.
- Column allowlist generated from `pricing/schema.py:FIELDS`, so a
  hallucinated column fails closed rather than silently returning nothing.
- Statement count of exactly one.
- Hard row cap on output and a wall-clock execution timeout, matching the
  posture of `LLM_TIMEOUT_SECONDS` in `pricing/assist.py`.

On rejection, feed the validator error back to the model for exactly one
retry, then fail with a clear message. No unbounded retry loop.

### 3. Execution

Read-only, in-memory, per-request. The analyst never reaches Neon, never sees
the governance tables, and cannot write. The frame it queries is the same
enriched frame the deterministic diagnostic already produced, so the analyst
and the readout cannot disagree about the underlying data.

### 4. Privacy boundary

This must not regress the posture documented in `pricing/assist.py`: only
aggregates and header names go to the provider, never row-level customer data.

The design is compatible with that, and the reason is structural: **generating
SQL requires the schema, not the data.** The model is given column names,
types, and the descriptions already written in `pricing/schema.py`. It is
never shown sample rows.

The exposure moves to the query *result*. Rule: if the result is row-level and
exceeds a small threshold, it is returned to the UI directly and the model is
given only its shape, column set, and row count to narrate. Aggregate results
below the threshold may be passed through. This needs an explicit constant and
a test, not a convention.

### 5. Provenance

Every answer carries `{question, sql, row_count, executed_at, result}`.

**The audit anchor is the stored SQL, not the question.** This matters more
than it looks. Executed code is reproducible, but the *generation* of that
code is not: the same question asked twice may produce two different valid
queries with two different answers. Anchoring the decision log to the question
would reintroduce exactly the non-determinism this design exists to prevent.
Anchoring it to the SQL means a logged decision can always be regenerated
exactly.

Follows: for the six canonical questions in `pricing/copilot.py`, the SQL
should be pinned and version-controlled, not generated per call. Generation is
for the open-ended tail.

## Failure modes

| Failure | Mitigation |
|---|---|
| Semantically valid but wrong SQL | Always show the query and row count, plus a plain-English restatement of what it did. Never hide the code behind the answer |
| Hallucinated column name | Validator allowlist from `schema.FIELDS`, one retry with the error fed back |
| Prompt injection via the question text | Question is data, never instruction. Validator is the real boundary, not the prompt |
| Expensive query as denial of service | Row cap plus wall-clock timeout |
| Answer drift across runs | Pin SQL for canonical questions; anchor the audit log to SQL |
| Buyer treats the analyst as the trusted path | Scope statement below, enforced in UI copy |

## What this explicitly does not do

- **Does not replace `pricing/metrics.py`.** The pre-built metrics remain the
  trusted path and the basis of the readout. The analyst answers follow-up
  questions. If the two ever disagree, the metrics module is correct by
  definition and the disagreement is a bug.
- **Does not write anything.** SELECT only, no CRM writeback, no state.
- **Does not produce governance verdicts.** A computed answer is not an
  approval, and must not appear in the approval path.
- **Does not widen the product into general RevOps analytics.** The single
  allowed table is the canonical deal view. This is a pricing analyst, not a
  business-intelligence surface.

## Testing

Business-logic tests are required here under the working agreement; this is
trust-critical, not CRUD.

- **Golden set.** Fixed questions with hand-written correct SQL and expected
  values against an existing fixture CSV. Asserts the executor, not the model.
- **Validator adversarial set.** DDL attempts, multi-statement payloads,
  hallucinated columns, file-system functions, injection strings in the
  question. Extends the existing pattern in
  `tests/test_adversarial_fixtures.py`.
- **Result-size boundary.** Asserts row-level results above the threshold are
  never passed to the provider.
- **Agreement test.** For questions that duplicate a `metrics.py` figure, the
  analyst's answer must match the deterministic one.

## Build slices

1. **Executor and validator, no model.** Hand-written SQL in, validated result
   out, full test suite. This is the trust-critical half and it is testable
   without any LLM call.
2. **Generation.** Model writes the SQL, one retry on validator error, answer
   returns with the query attached. Behind a flag, new endpoint, `/ask` left
   untouched.
3. **Provenance and UI.** Decision-log integration keyed on SQL, question-to-
   SQL cache, and the surface that shows the query next to the answer.

Slice 1 carries most of the risk and none of the model dependency, so it is
the honest place to stop and reassess.

## Open decisions

- DuckDB as a new dependency, or SQLite with a manual frame load.
- New `/analyst` endpoint versus extending `/ask`. Recommend new, so the
  existing RAG path and its citation contract are not disturbed.
- Whether slice 1 alone is enough to demo the "here is the query" claim to a
  prospect. It probably is, which affects sequencing.
