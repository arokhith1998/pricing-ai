---
title: Integration state — OpenAI review + Obsidian tooling
created: 2026-05-26
updated: 2026-05-26
tags: [decision, tooling, integrations, openai, obsidian]
status: active
---

# Integration state (2026-05-26)

Checked whether OpenAI and Obsidian were "synced." Both were NOT. Set up the Windows-safe subset of each.

## OpenAI (cross-model review)
- `openai` 2.38.0 installed. Review script at `tools/oai_review.py` (adversarial reviewer prompt;
  config via project `.env`, model from `OPENAI_REVIEW_MODEL`, default `gpt-4o`).
- **BLOCKED until** user puts `OPENAI_API_KEY` in `C:\Pricing-AI\.env` (gitignored). Key never pasted in chat.
- **Rule:** only our own code/docs go to OpenAI — never customer pricing data (egress + billing).

## Obsidian tooling (eugeniughelbur/obsidian-second-brain)
- Installed **project-scoped** (not global): skill → `.claude/skills/obsidian-second-brain/`,
  27 core commands → `.claude/commands/` (both gitignored; reproducible from `knowledge/`).
- `setup.sh` was NOT run — it needs `jq` (absent), wires a bash `PostCompact` hook (Windows-incompatible),
  and a `SessionStart` hook gated to cwd-inside-vault (our cwd is the project root).
- **Windows fix baked in:** `PYTHONUTF8=1` in `.claude/settings.local.json` env (scripts print emoji →
  cp1252 console crashes without it). `OBSIDIAN_VAULT_PATH` also set there.
- Smoke test: `vault_health.py` runs clean against `vault/` under UTF-8 mode.
- **Skipped (deliberate):** 6 research commands (Mac/keys: Grok, Perplexity, Gemini, YouTube),
  PostCompact bg-agent hook, SessionStart hook, MCP server (redundant — Claude Code uses filesystem directly).
- **Requires Claude Code restart** to activate the skill + `/obsidian-*` commands.

## Related
[[2026-05-26-kickoff-decisions]]
