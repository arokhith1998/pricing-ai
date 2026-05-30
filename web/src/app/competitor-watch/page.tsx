"use client";

import { useState } from "react";
import Reveal from "@/components/Reveal";

type Plan = {
  vendor: string;
  name: string;
  price_monthly: number | null;
  price_unit: string;
  billed_annually: boolean;
  included_usage: string;
  features: string[];
  notes: string;
};

type Match = {
  my_plan_name: string;
  competitor_vendor: string;
  competitor_plan_name: string;
  similarity: number;
  name_similarity: number;
  feature_similarity: number;
  price_delta_pct: number | null;
  pricing_position:
    | "above_market"
    | "at_market"
    | "below_market"
    | "unknown";
  features_only_mine: string[];
  features_only_theirs: string[];
  confidence: number;
};

type Comparison = {
  my_vendor: string;
  my_plans: Plan[];
  competitor_plans: Plan[];
  matches: Match[];
  summary: string;
};

function fmtMoney(v: number | null): string {
  if (v === null || !isFinite(v)) return "—";
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function PositionPill({ m }: { m: Match }) {
  const map: Record<Match["pricing_position"], { label: string; cls: string }> = {
    above_market: {
      label: "we cost more",
      cls: "border-coral/40 text-coral",
    },
    below_market: {
      label: "we cost less",
      cls: "border-teal/40 text-teal",
    },
    at_market: {
      label: "at market",
      cls: "border-mist text-fg",
    },
    unknown: {
      label: "no price comparable",
      cls: "border-mist text-muted",
    },
  };
  const info = map[m.pricing_position];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${info.cls}`}
    >
      {info.label}
      {m.price_delta_pct !== null
        ? ` ${m.price_delta_pct >= 0 ? "+" : ""}${Math.round(m.price_delta_pct * 100)}%`
        : ""}
    </span>
  );
}

function PlanCard({ p, accent = "border-mist" }: { p: Plan; accent?: string }) {
  return (
    <div className={`rounded-lg border ${accent} bg-surface-2 p-3`}>
      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-muted">
            {p.vendor || "—"}
          </div>
          <div className="text-base font-bold text-fg">{p.name}</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold tabular-nums text-fg">
            {fmtMoney(p.price_monthly)}
          </div>
          <div className="text-[10px] text-muted">
            {p.price_unit || (p.price_monthly !== null ? "monthly" : "")}
          </div>
        </div>
      </div>
      {p.included_usage ? (
        <div className="mt-1 text-xs text-muted">
          Included: {p.included_usage}
        </div>
      ) : null}
      {p.features.length > 0 ? (
        <ul className="mt-2 space-y-0.5 text-xs text-ink">
          {p.features.slice(0, 8).map((f, i) => (
            <li key={i}>
              <span className="text-teal">·</span> {f}
            </li>
          ))}
        </ul>
      ) : null}
      {p.notes ? (
        <div className="mt-2 text-[10px] italic text-muted">{p.notes}</div>
      ) : null}
    </div>
  );
}

export default function CompetitorWatchPage() {
  const [myUrl, setMyUrl] = useState("");
  const [compUrls, setCompUrls] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Comparison | null>(null);

  async function runCompare(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    if (!myUrl.trim()) {
      setError("Add your pricing page URL.");
      return;
    }
    setBusy(true);
    try {
      const r = await fetch("/api/matching", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "compare",
          my_url: myUrl.trim(),
          competitor_urls: compUrls
            .split("\n")
            .map((u) => u.trim())
            .filter(Boolean)
            .slice(0, 8),
        }),
      });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.error || "Matching failed.");
      }
      const data = (await r.json()) as Comparison;
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Matching failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <Reveal>
        <h1 className="text-2xl font-bold text-fg">Competitor watch</h1>
        <p className="mt-1 max-w-3xl text-slate">
          Drop your pricing page URL and up to eight competitor pricing pages.
          We extract structured plans from each, match yours against theirs,
          and tell you where you are above or below market — feature by
          feature.
        </p>
        <p className="mt-1 max-w-3xl text-xs text-muted">
          Customer-named competitors only. We do not scrape the market. Pages
          fetched once per hour, with <code>robots.txt</code> honored and a
          kill-switch list for any host that asks us to stop. By submitting a
          URL you warrant that you have the right to query it under the
          operator&rsquo;s terms (see{" "}
          <a href="/terms" className="underline hover:text-fg">/terms</a>).
          Plan extraction is AI-assisted; review results before acting.
        </p>
      </Reveal>

      <Reveal delay={0.04}>
        <form
          onSubmit={runCompare}
          className="space-y-3 rounded-xl border border-mist bg-surface p-5"
        >
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-muted">
              Your pricing page
            </label>
            <input
              type="url"
              value={myUrl}
              onChange={(e) => setMyUrl(e.target.value)}
              placeholder="https://yourcompany.com/pricing"
              className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-muted">
              Competitor pricing pages
              <span className="ml-2 text-[10px] font-normal text-muted">
                one URL per line · up to 8
              </span>
            </label>
            <textarea
              value={compUrls}
              onChange={(e) => setCompUrls(e.target.value)}
              placeholder={
                "https://competitor1.com/pricing\nhttps://competitor2.com/pricing"
              }
              rows={4}
              className="mt-1 w-full resize-none rounded-lg border border-mist bg-surface-2 px-3 py-2 font-mono text-sm text-ink focus:border-teal focus:outline-none"
            />
          </div>
          {error ? <div className="text-sm text-coral">{error}</div> : null}
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted">
              Plan extraction uses the cloud LLM; comparison runs locally with
              fastembed.
            </div>
            <button
              type="submit"
              disabled={busy || !myUrl}
              className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-bg transition hover:scale-[1.02] disabled:opacity-50"
            >
              {busy ? "Comparing…" : "Run comparison"}
            </button>
          </div>
        </form>
      </Reveal>

      {result ? (
        <>
          <Reveal delay={0.05}>
            <section className="space-y-3">
              <h2 className="text-lg font-semibold text-fg">
                Market position summary
              </h2>
              <p className="text-sm leading-relaxed text-ink">{result.summary}</p>
            </section>
          </Reveal>

          <Reveal delay={0.05}>
            <section className="space-y-3">
              <h2 className="text-lg font-semibold text-fg">
                Your plans ({result.my_vendor})
              </h2>
              {result.my_plans.length === 0 ? (
                <div className="rounded-lg border border-coral/40 bg-surface-2 p-3 text-sm text-coral">
                  We could not extract structured plans from your URL. Common
                  causes: the page is JS-heavy and the static fetch returns a
                  skeleton, or pricing is &quot;contact us&quot; only.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {result.my_plans.map((p, i) => (
                    <PlanCard key={i} p={p} accent="border-teal/30" />
                  ))}
                </div>
              )}
            </section>
          </Reveal>

          <Reveal delay={0.05}>
            <section className="space-y-3">
              <h2 className="text-lg font-semibold text-fg">
                Plan matches ({result.matches.length})
              </h2>
              {result.matches.length === 0 ? (
                <div className="rounded-lg border border-mist bg-surface-2 p-3 text-sm text-muted">
                  No high-confidence plan matches yet. Add more competitor URLs
                  or check the extracted plans below for shape.
                </div>
              ) : (
                <ul className="space-y-2">
                  {result.matches.map((m, i) => (
                    <li
                      key={i}
                      className="rounded-lg border border-mist bg-surface p-4"
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <div className="text-sm text-fg">
                          <span className="font-semibold">{m.my_plan_name}</span>{" "}
                          <span className="text-muted">vs</span>{" "}
                          <span className="font-semibold text-teal">
                            {m.competitor_vendor} · {m.competitor_plan_name}
                          </span>
                        </div>
                        <PositionPill m={m} />
                      </div>
                      <div className="mt-1 text-[11px] text-muted">
                        sim {Math.round(m.similarity * 100)}% (features{" "}
                        {Math.round(m.feature_similarity * 100)}% · name{" "}
                        {Math.round(m.name_similarity * 100)}%) ·{" "}
                        confidence {Math.round(m.confidence * 100)}%
                      </div>
                      <div className="mt-2 grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                        <div className="rounded border border-teal/30 bg-surface-2 p-2">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                            We have, they do not
                          </div>
                          {m.features_only_mine.length === 0 ? (
                            <div className="mt-1 text-muted">—</div>
                          ) : (
                            <ul className="mt-1 space-y-0.5">
                              {m.features_only_mine.map((f, j) => (
                                <li key={j} className="text-ink">
                                  + {f}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                        <div className="rounded border border-coral/30 bg-surface-2 p-2">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                            They have, we do not
                          </div>
                          {m.features_only_theirs.length === 0 ? (
                            <div className="mt-1 text-muted">—</div>
                          ) : (
                            <ul className="mt-1 space-y-0.5">
                              {m.features_only_theirs.map((f, j) => (
                                <li key={j} className="text-ink">
                                  − {f}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </Reveal>

          {result.competitor_plans.length > 0 ? (
            <Reveal delay={0.05}>
              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-fg">
                  Competitor plans extracted ({result.competitor_plans.length})
                </h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {result.competitor_plans.map((p, i) => (
                    <PlanCard key={i} p={p} />
                  ))}
                </div>
              </section>
            </Reveal>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
