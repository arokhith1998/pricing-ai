// Shared ADR-006 guard for the marketing pages. Ported from
// pricing/cost_basis.py (keep in sync with its allowlist): four negations,
// whole-phrase only, never followed by a figure. One more phrase is allowed
// here: the code-owned label for a customer-supplied cost basis
// (declared_cost under ADR-006 and ADR-007), used by the audit offer.
// Any other "margin" is a violation.
export const NEGATIONS = ["not margin", "never labeled margin", "not bookable margin", "not cost-based margin"];
export const DECLARED_LABEL = "contribution margin, customer-supplied cost basis";

const LEAD_IN =
  String.raw`(?:\.\.\.|…|[:,(–—])\s*[-−–]?\s*` +
  String.raw`(?:(?:about|roughly|around|nearly|over|under|approximately|circa|i\.e\.|e\.g\.)\s*,?\s*)?[\d$%]`;
const esc = (p: string) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const negationRe = new RegExp(
  String.raw`(?<![\w-])(?:` +
    NEGATIONS.map(esc).join("|") +
    String.raw`)(?=\s*$|\s*[^\w\s\-])(?!\s*` +
    LEAD_IN +
    ")",
  "gi",
);
// The label is a complete phrase and is exact: a different basis word breaks it.
const labelRe = new RegExp(String.raw`(?<![\w-])${esc(DECLARED_LABEL)}(?![\w-])`, "gi");

export function marginViolations(text: string): string[] {
  const covered = [...text.matchAll(negationRe), ...text.matchAll(labelRe)].map((m) => [
    m.index!,
    m.index! + m[0].length,
  ]);
  return [...text.matchAll(/margin/gi)]
    .filter((m) => !covered.some(([a, b]) => a <= m.index! && m.index! < b))
    .map((m) => text.slice(Math.max(0, m.index! - 30), m.index! + 22));
}

const LITERAL_RE = /"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`/g;
export function stringLiterals(source: string): string[] {
  return source.match(LITERAL_RE) ?? [];
}
