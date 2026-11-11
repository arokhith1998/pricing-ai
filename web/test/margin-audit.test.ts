import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  AT_RISK_BELOW,
  BAND_NAMES,
  DEFAULT_PRICE_SOURCES,
  WATCH_BELOW,
  audit,
  band,
  blendedPer1MTokens,
  compute,
  labels,
  validate,
  type AuditResult,
  type Band,
  type RawInputs,
  type ValidInputs,
} from "@/lib/margin-audit";

const DEFAULT_COST = 2.5; // test fixture only, not a price claim

function mustCompute(raw: RawInputs, d?: number): AuditResult {
  const v = validate(raw, { defaultCostPer1MTokens: d });
  if (!v.ok) throw new Error("expected valid: " + JSON.stringify(v));
  return compute(v.inputs);
}
const pctOf = (m: AuditResult["avg"]) => (m.pct.ok ? m.pct.value : NaN);

// Case A to D from design section 3.7. Unit is 1M tokens.
const A: RawInputs = { model: "flat", fee: 500, customers: 100, avgUsage: 2, p90Usage: 6, costPerUnit: 10, otherCost: 50, churn: 0.02 };
const B: RawInputs = { ...A, avgUsage: 20, p90Usage: 100, churn: 0.03 };
const C: RawInputs = { model: "usage", unitPrice: 20, costPerUnit: 10, otherCost: 50, customers: 100, avgUsage: 10, p90Usage: 30, churn: 0.02 };
const D: RawInputs = { model: "hybrid", fee: 300, unitPrice: 20, included: 10, costPerUnit: 10, otherCost: 50, customers: 50, avgUsage: 12, p90Usage: 30, churn: 0.02 };

describe("hand-computed reference cases", () => {
  it("A: flat, healthy", () => {
    const r = mustCompute(A);
    expect(r.avg.contribution).toBeCloseTo(430, 9);
    expect(pctOf(r.avg)).toBeCloseTo(0.86, 9);
    expect(r.p90.contribution).toBeCloseTo(390, 9);
    expect(pctOf(r.p90)).toBeCloseTo(0.78, 9);
    expect(r.breakEven).toEqual({ kind: "at", usage: 45 });
    expect(r.monthlyRevenue).toBeCloseTo(50000, 6);
    expect(r.monthlyCost).toBeCloseTo(7000, 6);
    expect(r.blendedPct).toBeCloseTo(0.86, 9);
    expect(r.p90OverBreakEven).toEqual({ ok: true, value: 6 / 45 });
    expect(r.revenueAtRiskShare).toBe(0);
    expect(r.band).toBe("healthy");
    expect(r.signal).toBe("STRUCTURE_COVERS_P90");
    expect(r.churnStepApplied).toBe(false);
    expect(r.lifetimeContribution).toBeCloseTo(430 / 0.02, 6);
  });

  it("B: flat, top decile underwater", () => {
    const r = mustCompute(B);
    expect(r.avg.contribution).toBeCloseTo(250, 9);
    expect(pctOf(r.avg)).toBeCloseTo(0.5, 9);
    expect(r.p90.contribution).toBeCloseTo(-550, 9);
    expect(r.breakEven).toEqual({ kind: "at", usage: 45 });
    expect(r.p90OverBreakEven.ok && r.p90OverBreakEven.value).toBeCloseTo(100 / 45, 9);
    expect(r.monthlyRevenue).toBeCloseTo(50000, 6);
    expect(r.monthlyCost).toBeCloseTo(25000, 6);
    expect(r.blendedPct).toBeCloseTo(0.5, 9);
    expect(r.revenueAtRiskShare).toBeCloseTo(0.1, 9);
    expect(r.topDecileShortfall).toBeCloseTo(5500, 6);
    expect(r.costCoveringFee).toEqual({ ok: true, value: 1050 });
    expect(r.band).toBe("at_risk");
    expect(r.signal).toBe("ADD_USAGE_COMPONENT");
    expect(r.deflation.map((d) => d.fall)).toEqual([0.25, 0.5]);
    expect(r.deflation[0].blendedPct).toBeCloseTo(0.6, 9);
    expect(r.deflation[1].blendedPct).toBeCloseTo(0.7, 9);
  });

  it("C: usage model, floor instead of break-even", () => {
    const r = mustCompute(C);
    expect(r.avg.revenue).toBe(200);
    expect(r.avg.cost).toBe(150);
    expect(r.avg.contribution).toBe(50);
    expect(pctOf(r.avg)).toBeCloseTo(0.25, 9);
    expect(r.p90.revenue).toBe(600);
    expect(r.p90.contribution).toBe(250);
    expect(pctOf(r.p90)).toBeCloseTo(250 / 600, 9);
    expect(r.breakEven).toEqual({ kind: "none" });
    expect(r.usageFloor).toEqual({ ok: true, value: 5 });
    expect(r.p90OverBreakEven.ok).toBe(false);
    expect(r.monthlyRevenue).toBeCloseTo(20000, 6);
    expect(r.monthlyCost).toBeCloseTo(15000, 6);
    expect(r.blendedPct).toBeCloseTo(0.25, 9);
    expect(r.band).toBe("at_risk");
    expect(r.signal).toBe("STRUCTURE_COVERS_P90"); // (20-10)/20 = 50%, not below 40%
    expect(r.costCoveringFee.ok).toBe(false);
  });

  it("D: hybrid, no break-even when p >= c", () => {
    const r = mustCompute(D);
    expect(r.avg.revenue).toBe(340);
    expect(r.avg.contribution).toBe(170);
    expect(r.p90.revenue).toBe(700);
    expect(r.p90.contribution).toBe(350);
    expect(r.bulkUsage).toBeCloseTo(10, 9);
    expect(r.monthlyRevenue).toBeCloseTo(17000, 6);
    expect(r.monthlyCost).toBeCloseTo(8500, 6);
    expect(r.blendedPct).toBeCloseTo(0.5, 9);
    expect(r.breakEven).toEqual({ kind: "none" });
    expect(r.band).toBe("watch");
    expect(r.signal).toBe("STRUCTURE_COVERS_P90");
    expect(r.predictabilityNote).toBe(false); // 30 / 12 = 2.5
  });

  it("E: churn step lowers Healthy to Watch", () => {
    const r = mustCompute({ ...A, churn: 0.1 });
    expect(r.lifetimeMonths).toBeCloseTo(10, 9);
    expect(r.bandBeforeChurn).toBe("healthy");
    expect(r.band).toBe("watch");
    expect(r.churnStepApplied).toBe(true);
    expect(labels(r).churnNote).toContain("lowered one step");
  });
});

describe("heavy-user break-even", () => {
  it("per seat: B is seat price times seats", () => {
    const r = mustCompute({ ...A, model: "per_seat", fee: 50, seats: 10 });
    expect(r.inputs.baseFee).toBe(500);
    expect(r.breakEven).toEqual({ kind: "at", usage: 45 });
  });
  it("flat with B <= s is negative before any usage", () => {
    const r = mustCompute({ ...A, fee: 40 });
    expect(r.breakEven).toEqual({ kind: "negative_before_usage" });
    expect(r.p90OverBreakEven.ok).toBe(false);
    expect(r.band).toBe("negative");
    expect(labels(r).breakEven).toContain("negative before any usage");
    const equal = mustCompute({ ...A, fee: 50 });
    expect(equal.breakEven).toEqual({ kind: "negative_before_usage" });
  });
  it("hybrid: break-even inside the allowance", () => {
    const r = mustCompute({ ...D, included: 30 });
    expect(r.breakEven).toEqual({ kind: "at", usage: 25 });
    expect(r.signal).toBe("FIX_OVERAGE_OR_ALLOWANCE");
  });
  it("hybrid: break-even in the overage when p < c", () => {
    const r = mustCompute({ ...D, unitPrice: 4 });
    // u1 = 25 > I = 10, u* = (300 - 50 - 4*10) / (10 - 4) = 35
    expect(r.breakEven.kind).toBe("at");
    expect(r.breakEven.kind === "at" && r.breakEven.usage).toBeCloseTo(35, 9);
    expect(r.signal).toBe("FIX_OVERAGE_OR_ALLOWANCE");
  });
  it("hybrid with B <= s is negative before usage", () => {
    expect(mustCompute({ ...D, fee: 40 }).breakEven).toEqual({ kind: "negative_before_usage" });
  });
  it("usage model with p <= c is negative at every level", () => {
    const r = mustCompute({ ...C, unitPrice: 8 });
    expect(r.breakEven).toEqual({ kind: "negative_at_every_level" });
    expect(r.usageFloor.ok).toBe(false);
    expect(r.band).toBe("negative");
    const eq = mustCompute({ ...C, unitPrice: 10 });
    expect(eq.breakEven).toEqual({ kind: "negative_at_every_level" });
  });
  it("usage floor is s / (p - c), and 0 only when s was typed 0", () => {
    expect(mustCompute({ ...C, otherCost: 0 }).usageFloor).toEqual({ ok: true, value: 0 });
    expect(mustCompute({ ...C, unitPrice: 15 }).usageFloor).toEqual({ ok: true, value: 10 });
  });
  it("usage model near cost raises UNIT_PRICE_NEAR_COST and the predictability note", () => {
    const r = mustCompute({ ...C, unitPrice: 15, avgUsage: 10, p90Usage: 30 });
    expect(r.signal).toBe("UNIT_PRICE_NEAR_COST"); // (15-10)/15 = 33%
    expect(r.predictabilityNote).toBe(true); // 30 / 10 = 3
  });
});

describe("four bands and their boundaries", () => {
  const bandOf = (b: Parameters<typeof band>[0]): Band => band(b);
  it("negative: average customer loses money, or blended below 0", () => {
    expect(bandOf({ avgContribution: -1, p90Contribution: 5, blendedPct: 0.5, p90OverBreakEven: null })).toBe("negative");
    expect(bandOf({ avgContribution: 1, p90Contribution: 5, blendedPct: -0.01, p90OverBreakEven: null })).toBe("negative");
  });
  it("at risk: blended below 40% or negative top decile", () => {
    expect(bandOf({ avgContribution: 1, p90Contribution: 5, blendedPct: 0.39, p90OverBreakEven: null })).toBe("at_risk");
    expect(bandOf({ avgContribution: 1, p90Contribution: -5, blendedPct: 0.9, p90OverBreakEven: null })).toBe("at_risk");
  });
  it("watch: blended below 60% or heavy customer within half of break-even", () => {
    expect(bandOf({ avgContribution: 1, p90Contribution: 5, blendedPct: 0.59, p90OverBreakEven: null })).toBe("watch");
    expect(bandOf({ avgContribution: 1, p90Contribution: 5, blendedPct: 0.9, p90OverBreakEven: 0.5 })).toBe("watch");
    expect(bandOf({ avgContribution: 1, p90Contribution: 5, blendedPct: 0.9, p90OverBreakEven: 0.49 })).toBe("healthy");
  });
  it("exposes the lines it uses", () => {
    expect([AT_RISK_BELOW, WATCH_BELOW]).toEqual([0.4, 0.6]);
  });
  it("blended exactly 0%, 40%, 60% through compute", () => {
    const usage = (p: number, c: number): RawInputs => ({ ...C, unitPrice: p, costPerUnit: c, otherCost: 0, avgUsage: 10, p90Usage: 20 });
    expect(mustCompute(usage(10, 10)).blendedPct).toBeCloseTo(0, 12);
    expect(mustCompute(usage(10, 10)).band).toBe("at_risk"); // 0 is not below 0
    expect(mustCompute(usage(50, 30)).band).toBe("watch"); // exactly 40%: not at risk
    expect(mustCompute(usage(25, 10)).band).toBe("healthy"); // exactly 60%: not watch
  });
  it("u90 exactly half of u*", () => {
    const base: RawInputs = { ...A, avgUsage: 3, p90Usage: 22.5 };
    const r = mustCompute(base);
    expect(r.band).toBe("watch");
    expect(r.signal).toBe("ADD_USAGE_COMPONENT");
    expect(mustCompute({ ...base, p90Usage: 22 }).band).toBe("healthy");
  });
  it("churn: 1/q = 12 exactly keeps the band, just under steps down", () => {
    expect(mustCompute({ ...A, churn: 1 / 12 }).band).toBe("healthy");
    expect(mustCompute({ ...A, churn: 0.0834 }).band).toBe("watch");
  });
  it("churn step: Watch to At risk, At risk and Negative stay", () => {
    expect(mustCompute({ ...D, churn: 0.2 }).band).toBe("at_risk");
    expect(mustCompute({ ...B, churn: 0.2 }).band).toBe("at_risk");
    expect(mustCompute({ ...A, fee: 40, churn: 0.2 }).band).toBe("negative");
  });
});

describe("validation, blanks and the never-zero rule", () => {
  it("a blank form is not enough and returns no figures", () => {
    const v = validate({});
    expect(v.ok).toBe(false);
    if (!v.ok) {
      expect(v.needed).toContain("model");
      expect("inputs" in v).toBe(false);
      const l = labels(v);
      expect(l.headline).toBe("Not enough to score.");
      expect(l.stillNeeded).toContain("Still needed:");
    }
  });
  it.each([
    ["fee", { fee: null }],
    ["customers", { customers: undefined }],
    ["avgUsage", { avgUsage: null }],
    ["p90Usage", { p90Usage: null }],
    ["otherCost", { otherCost: null }],
    ["churn", { churn: null }],
  ] as const)("blank %s is needed, never coerced", (field, patch) => {
    const v = validate({ ...A, ...patch }, { defaultCostPer1MTokens: DEFAULT_COST });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.needed).toEqual([field]);
  });
  it("blank storage cost is not enough, typed 0 scores and is echoed", () => {
    expect(validate({ ...A, otherCost: null }).ok).toBe(false);
    const v = validate({ ...A, otherCost: 0 });
    expect(v.ok).toBe(true);
    if (v.ok) {
      expect(v.notes.otherCostEnteredZero).toBe(true);
      expect(labels(compute(v.inputs), v.notes).otherCostEcho).toBe("You entered 0 for storage and other cost.");
      expect(compute(v.inputs).avg.contribution).toBe(480);
    }
  });
  it("typed 0 for included units is a real answer", () => {
    expect(validate({ ...D, included: 0 }).ok).toBe(true);
    expect(validate({ ...D, included: null }).ok).toBe(false);
  });
  it("typed cost 0 is rejected with the cost message", () => {
    const v = validate({ ...A, costPerUnit: 0 });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.errors[0]).toMatchObject({ field: "costPerUnit", code: "zero_cost", message: "Cost per unit must be more than 0." });
  });
  it("typed churn 0 is rejected", () => {
    const v = validate({ ...A, churn: 0 });
    expect(!v.ok && v.errors[0].code).toBe("zero_churn");
  });
  it("blank cost under 1M tokens uses the default only when one is supplied, and flags it", () => {
    const raw = { ...A, costPerUnit: null };
    expect(validate(raw).ok).toBe(false);
    const v = validate(raw, { defaultCostPer1MTokens: DEFAULT_COST });
    expect(v.ok && v.notes.defaultCostUsed).toBe(true);
    expect(v.ok && v.inputs.costPerUnit).toBe(DEFAULT_COST);
    expect(validate(raw, { defaultCostPer1MTokens: 0 }).ok).toBe(false);
  });
  it("blank cost under Other is not enough even with a default", () => {
    const v = validate({ ...A, unit: "other", unitLabel: "image", costPerUnit: null }, { defaultCostPer1MTokens: DEFAULT_COST });
    expect(v.ok).toBe(false);
    if (!v.ok) expect(v.needed).toEqual(["costPerUnit"]);
  });
  it("an explicit cost wins over the default and is not flagged", () => {
    const v = validate(A, { defaultCostPer1MTokens: DEFAULT_COST });
    expect(v.ok && v.notes.defaultCostUsed).toBe(false);
  });
  it("Other needs a 1 to 24 character label, trimmed", () => {
    const o: RawInputs = { ...A, unit: "other" };
    expect(validate(o).ok).toBe(false);
    expect(validate({ ...o, unitLabel: "   " }).ok).toBe(false);
    expect(validate({ ...o, unitLabel: "x".repeat(25) }).ok).toBe(false);
    const v = validate({ ...o, unitLabel: " image " });
    expect(v.ok && v.inputs.unitLabel).toBe("image");
  });
  it("negative, NaN, infinite and out-of-range inputs are rejected", () => {
    for (const patch of [
      { fee: -1 }, { fee: 0 }, { fee: NaN }, { fee: Infinity }, { fee: 1_000_001 },
      { customers: -5 }, { customers: 0 }, { customers: 1.5 }, { customers: 100_001 },
      { avgUsage: -1 }, { avgUsage: 0 }, { otherCost: -0.01 }, { costPerUnit: -3 },
      { churn: -0.1 }, { churn: 0.0005 }, { churn: 0.51 },
    ] as RawInputs[]) {
      const v = validate({ ...A, ...patch });
      expect(v.ok, JSON.stringify(patch)).toBe(false);
      if (!v.ok) expect(v.errors.length, JSON.stringify(patch)).toBeGreaterThan(0);
    }
    expect(validate({ ...A, p90Usage: -6 }).ok).toBe(false);
    expect(validate({ ...D, unitPrice: -1 }).ok).toBe(false);
    expect(validate({ ...D, included: -1 }).ok).toBe(false);
    expect(validate({ ...A, model: "per_seat", seats: 0 }).ok).toBe(false);
    expect(validate({ ...A, model: "per_seat", seats: 2.5 }).ok).toBe(false);
    expect(validate({ ...A, model: "tiered" as never }).ok).toBe(false);
  });
  it("fields not shown for the chosen model are ignored", () => {
    expect(validate({ ...A, unitPrice: -9, included: -9, seats: -9 }).ok).toBe(true);
  });
  it("u90 below average and above ten times average are rejected", () => {
    const low = validate({ ...A, avgUsage: 10, p90Usage: 9 });
    expect(!low.ok && low.errors[0].code).toBe("p90_below_avg");
    const high = validate({ ...A, avgUsage: 2, p90Usage: 20.5 });
    expect(!high.ok && high.errors[0].code).toBe("p90_above_multiple");
    expect(validate({ ...A, avgUsage: 2, p90Usage: 2 }).ok).toBe(true);
    expect(validate({ ...A, avgUsage: 2, p90Usage: 20 }).ok).toBe(true);
  });
  it("audit() returns no result when validation fails", () => {
    expect("result" in audit({})).toBe(false);
    expect("result" in audit(A)).toBe(true);
  });
});

describe("deflation and properties", () => {
  it("held-price deflation: c replaced by c x (1 - d)", () => {
    const r = mustCompute(A);
    // c = 7.5: C_tot = 100 x (15 + 50) = 6,500; 1 - 6500/50000 = 0.87
    expect(r.deflation[0].blendedPct).toBeCloseTo(0.87, 9);
    // c = 5: C_tot = 100 x (10 + 50) = 6,000; 1 - 6000/50000 = 0.88
    expect(r.deflation[1].blendedPct).toBeCloseTo(0.88, 9);
  });
  it("seeded property loop", () => {
    let seed = 20261110;
    const rnd = () => {
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const rank: Record<Band, number> = { negative: 0, at_risk: 1, watch: 2, healthy: 3 };
    for (let k = 0; k < 300; k++) {
      const model = (["flat", "usage", "hybrid", "per_seat"] as const)[Math.floor(rnd() * 4)];
      const avgUsage = 1 + rnd() * 100;
      const raw: RawInputs = {
        model, fee: 10 + rnd() * 5000, seats: 1 + Math.floor(rnd() * 20), unitPrice: 0.5 + rnd() * 40,
        included: rnd() * 50, customers: 1 + Math.floor(rnd() * 1000), avgUsage,
        p90Usage: avgUsage * (1 + rnd() * 9), costPerUnit: 0.1 + rnd() * 30, otherCost: rnd() * 200,
        churn: 0.005 + rnd() * 0.2,
      };
      const r = mustCompute(raw);
      const i = r.inputs;
      expect(r.monthlyCost).toBeCloseTo(i.customers * (i.costPerUnit * i.avgUsage + i.otherCost), 6);
      expect(0.9 * r.bulkUsage + 0.1 * i.p90Usage).toBeCloseTo(i.avgUsage, 9);
      const worse = mustCompute({ ...raw, costPerUnit: (raw.costPerUnit as number) * 1.5 });
      expect(rank[worse.band]).toBeLessThanOrEqual(rank[r.band]);
      expect(JSON.stringify(compute(i))).toBe(JSON.stringify(r)); // deterministic
    }
  });
  it("same inputs, identical output", () => {
    expect(mustCompute(B)).toEqual(mustCompute(B));
  });
});

describe("default unit price sources", () => {
  it("names the three provider pages and invents no number", () => {
    expect(DEFAULT_PRICE_SOURCES).toHaveLength(3);
    for (const s of DEFAULT_PRICE_SOURCES) expect(new URL(s.url).protocol).toBe("https:");
    expect(blendedPer1MTokens(2, 10)).toBeCloseTo(4, 12); // 0.75 x 2 + 0.25 x 10
  });
});

// ---- Label rules (ADR-006, F1) ---------------------------------------------

const pyPath = fileURLToPath(new URL("../../pricing/cost_basis.py", import.meta.url));
const py = readFileSync(pyPath, "utf8");
// Port of cost_basis.allowed_phrases(); the parity test below pins it to the Python source.
const ALLOWED = ["not margin", "never labeled margin", "not bookable margin", "not cost-based margin"];
const BASIS = "contribution margin, customer-supplied cost basis";

/** Occurrences of "margin" left after removing the caption and whole-phrase ADR-006 negations. */
function stray(text: string): string[] {
  let t = text.split(BASIS).join("");
  for (const p of ALLOWED) t = t.replace(new RegExp(`(?<![\\w-])${p}(?=\\s*$|\\s*[^\\w\\s-])`, "gi"), "");
  return [...t.matchAll(/margin/gi)].map((m) => t.slice(Math.max(0, m.index - 20), m.index + 20));
}

const BANNED = [
  "proven", "guarantee", "autonomous", "automatically set", "ai-powered", "learns from",
  "customers like you", "peers", "industry average", "gross margin", "net margin", "verified",
  "true margin", "actual margin", "save you", "recover",
];

function allText(r: AuditResult, zero = false): string[] {
  const l = labels(r, { otherCostEnteredZero: zero });
  return Object.entries(l).filter(([, v]) => typeof v === "string" && v).map(([, v]) => v as string);
}

describe("labels", () => {
  const fixtures: Record<string, RawInputs> = {
    A, B, C, D, E: { ...A, churn: 0.1 }, negative: { ...A, fee: 40 }, perSeat: { ...B, model: "per_seat", fee: 50, seats: 10 },
    usageNeg: { ...C, unitPrice: 8 }, nearCost: { ...C, unitPrice: 15 }, hybridLeak: { ...D, unitPrice: 4 }, zeroStorage: { ...A, otherCost: 0 },
  };

  it("pins the basis caption and the four negations to pricing/cost_basis.py", () => {
    expect(py).toContain(`DECLARED_COST: "${BASIS}"`);
    for (const p of ALLOWED) expect(py).toContain(`"${p}"`);
    expect(labels(mustCompute(A)).basis).toBe(BASIS);
  });

  it("the word margin appears only as the caption or an allowlisted negation", () => {
    for (const [name, raw] of Object.entries(fixtures)) {
      for (const text of allText(mustCompute(raw), name === "zeroStorage")) {
        expect(stray(text), `${name}: ${text}`).toEqual([]);
      }
    }
    const nl = labels({ ok: false, needed: ["fee", "churn"], errors: [] });
    expect(stray(JSON.stringify(nl))).toEqual([]);
  });

  it("the stray-word checker itself catches affirmative use and passes the allowlist", () => {
    expect(stray("gross margin 40%")).not.toEqual([]);
    expect(stray("Margin is thin")).not.toEqual([]);
    expect(stray("not margin compression")).not.toEqual([]);
    expect(stray(`${BASIS}`)).toEqual([]);
    for (const p of ALLOWED) expect(stray(`The figure is ${p}.`)).toEqual([]);
  });

  it("contains no banned phrase, em dash or en dash", () => {
    for (const [name, raw] of Object.entries(fixtures)) {
      for (const text of allText(mustCompute(raw))) {
        const low = text.toLowerCase();
        for (const b of BANNED) expect(low.includes(b), `${name}: "${b}" in ${text}`).toBe(false);
        expect(/[–—]/.test(text), text).toBe(false);
      }
    }
  });

  it("benchmark appears only where it is negated", () => {
    for (const text of allText(mustCompute(A))) {
      if (/benchmark/i.test(text)) expect(text).toContain("not industry benchmarks");
    }
  });

  it("band names are the four words and nothing else", () => {
    expect(Object.values(BAND_NAMES)).toEqual(["Negative", "At risk", "Watch", "Healthy"]);
  });

  it("formats figures from the inputs", () => {
    const a = labels(mustCompute(A));
    expect(a.avg).toBe("An average customer leaves $430.00 a month (86.0%).");
    expect(a.breakEven).toBe("Contribution turns negative above 45 1M tokens a month per customer.");
    const b = labels(mustCompute(B));
    expect(b.p90).toBe("A customer at the 90th percentile loses $550.00 a month (-110.0%).");
    expect(b.revenueAtRisk).toContain("At least 10.0% of revenue");
    expect(b.signal).toContain("$1,050.00");
    expect(b.deflation).toContain("from 50.0% to 60.0%");
    expect(b.deflation).toContain("to 70.0%");
    expect(labels(mustCompute(C)).usageFloor).toBe("Each customer must use at least 5 1M tokens a month to cover storage and other cost.");
    expect(labels(mustCompute(A)).revenueAtRisk).toContain("No revenue sits");
  });

  it("every label set carries the basis caption and note", () => {
    const l = labels(mustCompute(D));
    expect(l.basis).toBe(BASIS);
    expect(l.basisNote).toContain("has not checked them against a billing or cost system");
  });

  it("is not enough: no band, no number", () => {
    const l = labels({ ok: false, needed: ["churn"], errors: [] });
    expect(l).toEqual({ state: "not_enough", headline: "Not enough to score.", stillNeeded: "Still needed: Monthly churn.", errors: [] });
  });
});

// Typing guard: ValidInputs cannot be built from raw numbers by accident.
const _typeCheck: ValidInputs | null = null;
void _typeCheck;
