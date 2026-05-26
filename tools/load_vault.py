"""Print a compact snapshot of the Obsidian vault for a SessionStart hook.

Wired in .claude/settings.json so its stdout is injected into context at the
start of every Claude session — the "keep feeding off the vault" half of the
second-brain workflow. Reads OBSIDIAN_VAULT_PATH (set in settings) so it keeps
working if the vault later moves to its own repo.

Lean by design: prints the vault operating manual + an index of note titles by
folder + the most recently touched notes. It does NOT dump note bodies — Claude
reads those on demand. Keeps per-session context cost small.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

MAX_NOTES = 120          # cap the index so context stays bounded
RECENT = 8               # how many recently-modified notes to surface


def _title(md: Path) -> str:
    """Best-effort note title: frontmatter `title:` else the filename stem."""
    try:
        head = md.read_text(encoding="utf-8", errors="ignore")[:600]
    except OSError:
        return md.stem
    for line in head.splitlines():
        s = line.strip()
        if s.startswith("title:"):
            t = s[len("title:"):].strip().strip("'\"")
            if t:
                return t
    return md.stem


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows-safe
    vault = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "vault"))
    if not vault.is_dir():
        print(f"[vault] No vault at {vault} (set OBSIDIAN_VAULT_PATH).")
        return 0

    notes = sorted(
        (p for p in vault.rglob("*.md") if ".obsidian" not in p.parts),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )

    print(f"# Obsidian vault snapshot ({vault})")
    print(f"{len(notes)} notes. Consult before answering domain questions; "
          "write decisions/logs back (see vault/_CLAUDE.md).\n")

    manual = vault / "_CLAUDE.md"
    if manual.exists():
        print("## Vault operating manual (_CLAUDE.md)")
        print(manual.read_text(encoding="utf-8", errors="ignore").strip())
        print()

    if notes:
        print(f"## Recently updated (top {RECENT})")
        for p in notes[:RECENT]:
            print(f"- [{_title(p)}]({p.relative_to(vault).as_posix()})")
        print()

    print("## Note index by folder")
    by_folder: dict[str, list[Path]] = {}
    for p in notes[:MAX_NOTES]:
        folder = p.relative_to(vault).parent.as_posix()
        by_folder.setdefault("(root)" if folder == "." else folder, []).append(p)
    for folder in sorted(by_folder):
        print(f"\n### {folder}")
        for p in sorted(by_folder[folder]):
            print(f"- {_title(p)}  ·  {p.relative_to(vault).as_posix()}")
    if len(notes) > MAX_NOTES:
        print(f"\n…and {len(notes) - MAX_NOTES} more.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
