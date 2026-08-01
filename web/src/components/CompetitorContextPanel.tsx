"use client";

import { useEffect, useState } from "react";

type Source = {
  id: string;
  competitor_name: string;
  source_url: string;
  source_type: string;
  summary: string;
  confidence: "high" | "medium" | "low";
  claims: Array<{
    claim: string;
    confidence: "high" | "medium" | "low";
    evidence_excerpt: string;
  }>;
  captured_at: string;
  last_verified_at: string;
};

const TYPES = [
  ["pricing", "Pricing page"],
  ["documentation", "Product documentation"],
  ["release_notes", "Release notes"],
  ["case_study", "Case study"],
  ["funding", "Funding announcement"],
  ["executive_interview", "Executive interview"],
  ["investor_material", "Quarterly / investor material"],
  ["other", "Other public source"],
] as const;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(body.error || "Competitor context request failed.");
  return body;
}

export default function CompetitorContextPanel() {
  const [sources, setSources] = useState<Source[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("pricing");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clock] = useState(() => Date.now());

  useEffect(() => {
    let active = true;
    request<{ sources: Source[] }>("/api/competitor-context")
      .then((result) => {
        if (active) setSources(result.sources);
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load sources.");
      });
    return () => {
      active = false;
    };
  }, []);

  async function add(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await request<{ source: Source }>("/api/competitor-context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          competitor_name: name,
          source_url: url,
          source_type: type,
        }),
      });
      setSources((current) => [
        result.source,
        ...current.filter((source) => source.id !== result.source.id),
      ]);
      setUrl("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not verify the source.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    setError("");
    try {
      await request(`/api/competitor-context?id=${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      setSources((current) => current.filter((source) => source.id !== id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not remove the source.");
    } finally {
      setBusy(false);
    }
  }

  const competitors = new Set(sources.map((source) => source.competitor_name.toLowerCase())).size;
  return (
    <section className="rounded-xl border border-mist bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-fg">Sourced competitor context</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate">
            Select 3-10 named competitors and add their public sources. Pricekeel extracts qualitative claims with source, capture date, and confidence. This evidence never moves the discount guardrail.
          </p>
        </div>
        <div className="rounded-full border border-mist px-3 py-1 text-xs text-muted">
          {competitors}/10 competitors · {sources.length} sources
        </div>
      </div>
      <form onSubmit={add} className="mt-4 grid gap-3 lg:grid-cols-[0.8fr_1.4fr_1fr_auto]">
        <input value={name} onChange={(event) => setName(event.target.value)} required placeholder="Competitor name" className="rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink" />
        <input type="url" value={url} onChange={(event) => setUrl(event.target.value)} required placeholder="https://public-source.example/..." className="rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink" />
        <select value={type} onChange={(event) => setType(event.target.value)} className="rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink">{TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
        <button type="submit" disabled={busy} className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50">{busy ? "Verifying…" : "Add source"}</button>
      </form>
      {error ? <div className="mt-3 text-sm text-coral">{error}</div> : null}
      <div className="mt-5 space-y-3">
        {sources.map((source) => {
          const days = Math.max(0, Math.floor((clock - new Date(source.last_verified_at).getTime()) / 86_400_000));
          const stale = days > 90;
          return (
            <article key={source.id} className="rounded-lg border border-mist bg-surface-2 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-fg">{source.competitor_name}</div>
                  <a href={source.source_url} target="_blank" rel="noreferrer" className="break-all text-xs text-teal underline">{source.source_url}</a>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider">
                  <span className="rounded-full border border-mist px-2 py-1 text-muted">{source.source_type.replaceAll("_", " ")}</span>
                  <span className={`rounded-full border px-2 py-1 ${stale ? "border-coral/40 text-coral" : "border-teal/40 text-teal"}`}>{stale ? `stale · ${days}d` : `verified · ${days}d`}</span>
                  <button type="button" onClick={() => remove(source.id)} disabled={busy} className="text-muted hover:text-coral">Remove</button>
                </div>
              </div>
              {source.summary ? <p className="mt-3 text-sm text-slate">{source.summary}</p> : null}
              <ul className="mt-3 space-y-2">
                {source.claims.map((claim, index) => <li key={`${source.id}-${index}`} className="text-sm text-ink"><span className="mr-2 text-xs font-semibold uppercase text-teal">{claim.confidence}</span>{claim.claim}{claim.evidence_excerpt ? <div className="mt-0.5 text-xs italic text-muted">Evidence: “{claim.evidence_excerpt}”</div> : null}</li>)}
              </ul>
              <div className="mt-3 text-[11px] text-muted">Captured {new Date(source.captured_at).toLocaleDateString()} · last verified {new Date(source.last_verified_at).toLocaleDateString()} · overall confidence {source.confidence}</div>
            </article>
          );
        })}
        {!sources.length ? <div className="rounded-lg border border-dashed border-mist p-4 text-sm text-muted">No sources yet. Investor materials are useful mainly for public companies; pricing pages, docs, release notes, and case studies are usually stronger for private B2B SaaS competitors.</div> : null}
      </div>
    </section>
  );
}
