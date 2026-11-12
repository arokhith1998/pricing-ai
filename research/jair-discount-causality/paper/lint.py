"""Static checks on main.tex for a machine without TeX: balanced braces and
environments, every \\cite key in refs.bib, every \\ref with a \\label, every
\\input file present, no em dashes. Not a substitute for compiling.

Run:  python research/jair-discount-causality/paper/lint.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
tex = (HERE / "main.tex").read_text(encoding="utf-8")
bib = (HERE / "refs.bib").read_text(encoding="utf-8")
body = "\n".join(line.split("%")[0] if not line.lstrip().startswith("%") else ""
                 for line in tex.replace("\\%", "PCT").splitlines())
problems = []

depth = 0
for ch in body.replace("\\{", "").replace("\\}", ""):
    depth += ch == "{"
    depth -= ch == "}"
    if depth < 0:
        problems.append("closing brace before opening brace")
        break
if depth:
    problems.append(f"unbalanced braces: depth {depth} at end of file")

stack = []
for kind, name in re.findall(r"\\(begin|end)\{([^}]+)\}", body):
    if kind == "begin":
        stack.append(name)
    elif not stack or stack.pop() != name:
        problems.append(f"\\end{{{name}}} does not match")
if stack:
    problems.append(f"unclosed environments: {stack}")

if body.count("$") % 2:
    problems.append("odd number of $ signs")

keys = set(re.findall(r"@\w+\{([^,]+),", bib))
cited = {k.strip() for group in re.findall(r"\\cite[tp]?\{([^}]+)\}", body)
         for k in group.split(",")}
problems += [f"cited but not in refs.bib: {k}" for k in sorted(cited - keys)]
unused = sorted(keys - cited)

labels = set(re.findall(r"\\label\{([^}]+)\}", body))
refs = set(re.findall(r"\\(?:eq)?ref\{([^}]+)\}", body))
problems += [f"\\ref without \\label: {r}" for r in sorted(refs - labels)]

for f in re.findall(r"\\input\{([^}]+)\}", body):
    if not (HERE / f"{f}.tex").exists():
        problems.append(f"missing input file: {f}.tex")
for f in re.findall(r"\{(data/[^}]+)\}", body):
    if not (HERE / f).exists():
        problems.append(f"missing data file: {f}")

if "\u2014" in tex or "\u2014" in bib:
    problems.append("em dash found")

print(f"{len(cited)} citations, {len(labels)} labels, {len(refs)} references, "
      f"{body.count(chr(92) + "todo{") - 1} TODO markers")
if unused:
    print("in refs.bib but not cited:", ", ".join(unused))
for p in problems:
    print("PROBLEM:", p)
sys.exit(1 if problems else 0)
