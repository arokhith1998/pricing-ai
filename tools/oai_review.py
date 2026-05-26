#!/usr/bin/env python
"""Cross-model review: send our own code/docs to an OpenAI model for adversarial critique.

This is the "second pair of eyes" on what Claude produces. It deliberately asks the
reviewer to be blunt and find problems.

RULES (enforced by convention, not code):
  - Only OUR OWN artifacts (code, design docs, SQL, configs) go through here.
  - NEVER send customer pricing data, deal data, or any third-party confidential data.
    That data leaves the environment and lands on OpenAI's servers + bills the account.

Usage:
  python tools/oai_review.py path/to/file.py [more/files ...]
  python tools/oai_review.py --diff                 # review staged+unstaged git diff
  python tools/oai_review.py --stdin                 # review piped text
  python tools/oai_review.py file.py --context "Focus on the leakage metric math"

Config (in C:\\Pricing-AI\\.env, gitignored — never commit the key):
  OPENAI_API_KEY=sk-...
  OPENAI_REVIEW_MODEL=gpt-4o      # optional; set to whatever you have access to
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = (
    "You are a senior staff engineer and B2B SaaS pricing domain expert. You are reviewing "
    "work produced by another AI (Claude) on a pricing-intelligence platform. Be direct and "
    "adversarial; do not flatter. Your job is to find problems, not praise. For each issue give: "
    "(1) severity [blocker/major/minor/nit], (2) the specific location, (3) why it's wrong or risky, "
    "(4) a concrete fix. Cover correctness bugs, wrong/misleading pricing metric definitions "
    "(discount leakage, price realization, win-rate-by-band, NRR/GRR), missing tests, "
    "data-quality assumptions, and explainability gaps. If something is actually fine, say so briefly "
    "and move on. End with the single most important thing to fix first."
)


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader so we avoid a python-dotenv dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def gather_input(args: argparse.Namespace) -> str:
    if args.stdin:
        return sys.stdin.read()
    if args.diff:
        diff = subprocess.run(
            ["git", "diff", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True
        ).stdout
        if not diff.strip():
            diff = subprocess.run(
                ["git", "diff"], cwd=PROJECT_ROOT, capture_output=True, text=True
            ).stdout
        return diff or "(no diff found)"
    chunks: list[str] = []
    for p in args.paths:
        fp = Path(p)
        if not fp.exists():
            print(f"warning: skipping missing path {p}", file=sys.stderr)
            continue
        chunks.append(f"===== FILE: {fp} =====\n{fp.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAI cross-model review of our own artifacts.")
    parser.add_argument("paths", nargs="*", help="files to review")
    parser.add_argument("--diff", action="store_true", help="review git diff instead of files")
    parser.add_argument("--stdin", action="store_true", help="review text from stdin")
    parser.add_argument("--context", default="", help="extra instruction for the reviewer")
    args = parser.parse_args()

    _load_dotenv(PROJECT_ROOT / ".env")

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY not set. Put it in C:\\Pricing-AI\\.env (gitignored):\n"
            "  OPENAI_API_KEY=sk-...\n"
            "Do NOT paste the key into chat.",
            file=sys.stderr,
        )
        return 2

    content = gather_input(args)
    if not content.strip():
        print("ERROR: nothing to review (no files / empty diff / empty stdin).", file=sys.stderr)
        return 2

    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: python -m pip install openai", file=sys.stderr)
        return 2

    model = os.environ.get("OPENAI_REVIEW_MODEL", "gpt-4o")
    user_msg = content if not args.context else f"REVIEW FOCUS: {args.context}\n\n{content}"

    client = OpenAI()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001 - surface any API error plainly
        print(f"ERROR calling OpenAI ({model}): {exc}", file=sys.stderr)
        return 1

    print(f"# OpenAI review ({model})\n")
    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
