# Pricekeel AI layer, re-evaluation 2026-09-27 (read-only, tree 00bd935)

## Verification of the PR #69 closures

All verified against the working tree, not the docs.

- Anthropic only: `pricing/assist.py:79-81` (`has_llm` checks only `ANTHROPIC_API_KEY`), `:140-154` (single `Anthropic(...).messages.create`). No `openai` import anywhere under `pricing/` or `api/`; the only OpenAI code is `tools/oai_review.py` and `tools/oai_panel*.py`, which never import `assist`. Pinned by `tests/test_assist.py:104`.
- Model ids as configuration: `assist.py:43-44` (`claude-sonnet-5`, `claude-haiku-4-5`), env override at `:143-146`, tested at `test_assist.py:284-313`. Both are current generation per the claude-api reference.
- Em dashes forbidden in all three narration prompts: `assist.py:237`, `copilot.py:643-644`, `rag.py:274-275`. Each has a test (`test_assist.py:497`, `test_copilot.py:299`, `test_rag.py:216`). Gap: `matching.py` has three more prompts (`_CONTEXT_SYSTEM:286`, `_EXTRACT_SYSTEM:399`, `_SUMMARY_SYSTEM:776`) with no em-dash rule. Two are JSON-only, but `_SUMMARY_SYSTEM` writes user-visible prose.
- Deal-level arrays stripped: `rag.py:98-117` (`_strip_deal_level`), applied at `:294` before serialization at `:303`. Tested `test_rag.py:120-157`, including a generic sweep for unlisted keys.
- Competitor price verified against page text: `matching.py:471-487` (`_price_verified_in_text`), applied at `:531-551`; an unverified price is flagged `price_low_confidence` and excluded from `price_delta_pct` at `:705-709`. Tested `test_matching.py:522-620`.
- `llm_fallback_failed`: `mapping.py:320,374,390`; tested `test_mapping.py:151-163`.
- Missing-vs-zero and degraded in copilot: `copilot.py:164-180` (`_flag_missing`), `:110-111,123-124` (Answer fields), `:652-691` (prompt note and no-LLM branch). Tested `test_copilot.py:214-286`.
- `tests/test_rag.py` and `tests/test_mapping.py` exist. Injection: `test_rag.py:167-205` and `test_matching.py:584-620`. Header subset: `test_mapping.py:111-145`.

## What is still missing

1. Sentinel wrapping. Untrusted text still lands in the user turn as bare text: `rag.py:313` (`[D1] From 'x':\n{text}`), `matching.py:507` (`PAGE TEXT (verbatim):`), `matching.py:352-357` (raw `page_text` inside the JSON). The only defense is the rag system prompt sentence at `rag.py:270-272`; the matching prompts have no equivalent. The rag injection test is structural (stubbed `_complete`, asserts citation counts built by code), so it proves nothing about the model's behavior under injection.
2. Caching. No memoization of narration anywhere: `executive_summary` (`assist.py:244`), `answer_canonical` (`copilot.py:688`), `ask` (`rag.py:345`), `_summarize_matches` (`matching.py:803`) all call the provider fresh. `summary_facts` and the opportunities list are deterministic, so a `sha256(system + user_msg + model)` key with a short TTL is trivially correct and would also make outputs reproducible for support.
3. Cost per request. Nothing reads `response.usage`; `_complete` (`assist.py:154-177`) discards it. Estimates at current list rates (Sonnet 5 $2/$10 per MTok, Haiku 4.5 $1/$5): executive summary ~$0.003; copilot answer ~$0.005 to $0.007; RAG ask ~$0.011 (6,000-char analysis, four 1,200-char chunks, 700 max output); per competitor URL on Haiku ~$0.01 to $0.012 (30K-char page cap, 1,500 max output); match summary on Sonnet ~$0.006. A three-URL compare is roughly $0.05. Cents, not a margin problem, but unmeasured.
4. Eval gaps. No test asserts a citation marker appears in a rag answer (the "uncited claim is a bug" rule is prompt-only). No live or recorded-response eval for any prompt; every LLM test stubs `_complete`. `docs.py` still has no test file. `matching` summary prose has no em-dash test.

## Updated verdict

Findings 1 through 5 from 2026-09-26 are closed in code with tests, not just in the closure note. The layer now enforces its two hard rules (LLM never computes a number; row-level data never leaves) at the boundary, and both failure paths that used to go quiet now log and flag. What remains is second-order: the injection surface is documented and partially tested but not hardened, and provider spend is neither cached nor measured.

## The one thing next week

Wrap every untrusted block (doc chunks in `rag.ask`, page text in both `matching` extractors) in an explicit sentinel, tell all four affected system prompts that anything inside the sentinel is data, and extend the two existing injection fixtures to assert the sentinel is present in the captured prompt. While in `_complete`, log `response.usage` per call; that is five lines and turns the cost estimates above into numbers.
