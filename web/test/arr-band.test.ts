import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

// PK-112: the decided ICP band is "$10M to $100M ARR, gated on deal volume"
// (vault/Decisions/2026-09-11). "$20M to $100M" is named drift. Pin it site-wide.

const ROOT = join(__dirname, "..", "src");
const DIRS = [join(ROOT, "app"), join(ROOT, "components")];
const EXT = /\.(tsx?|mdx?)$/;

// Allowlist for legitimate non-band figures. The LeadForm revenue options
// currently contain none of the banned strings, so this stays empty.
const ALLOW: string[] = [];

const BANNED = [/\$20M/, /\$20 to 100M/, /20M to 100M/, /\$20(?:–|—|-)100M/, /\$20 ?to ?\$100M/];

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (EXT.test(name)) out.push(p);
  }
  return out;
}

describe("ICP ARR band", () => {
  const files = DIRS.flatMap(walk);

  it("scans a non-trivial set of sources", () => {
    expect(files.length).toBeGreaterThan(20);
  });

  it("never states the drifted $20M to $100M band", () => {
    const hits: string[] = [];
    for (const f of files) {
      const rel = relative(ROOT, f).split("\\").join("/");
      if (ALLOW.includes(rel)) continue;
      const src = readFileSync(f, "utf8");
      for (const re of BANNED) if (re.test(src)) hits.push(`${rel}: ${re}`);
    }
    expect(hits).toEqual([]);
  });

  it("the social card carries no ARR band (F14), and the pricing page is gone (F17)", () => {
    const og = readFileSync(join(ROOT, "app/opengraph-image.tsx"), "utf8");
    expect(existsSync(join(ROOT, "app/pricing/page.tsx"))).toBe(false);
    expect(og).not.toMatch(/ARR/);
    expect(og).not.toMatch(/\$\d+\s?M/);
  });
});
