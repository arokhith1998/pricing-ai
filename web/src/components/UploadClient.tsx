"use client";

import { useMemo, useState } from "react";
import type { Diagnostic } from "@/lib/api";
import { money, pct } from "@/lib/format";
import WinRateChart from "@/components/charts/WinRateChart";
import SegmentChart from "@/components/charts/SegmentChart";
import LeakageBars from "@/components/LeakageBars";

// --- shape ------------------------------------------------------------------

type Confidence = "high" | "medium" | "low" | "none";
type MapResponse = {
  mapping: Record<string, string | null>;
  confidence: Record<string, Confidence>;
  used: Record<string, string>;
  headers: string[];
  sample: Record<string, string>[];
};

const REQUIRED_FIELDS = [
  "opportunity_id", "account_name", "outcome", "created_date", "close_date",
  "segment", "product_tier", "value_metric", "list_acv", "booked_acv",
] as const;

const FIELD_LABEL: Record<string, string> = {
  opportunity_id: "Opportunity ID",
  account_id: "Account ID",
  account_name: "Account",
  outcome: "Outcome",
  created_date: "Created",
  close_date: "Close date",
  segment: "Segment",
  region: "Region",
  industry: "Industry",
  business_unit: "Business unit",
  product_line: "Product line",
  product_family: "Product family",
  product_tier: "Plan",
  sku: "SKU",
  value_metric: "Pricing model",
  list_acv: "List value (annual)",
  booked_acv: "Booked value (annual)",
  platform_fee_acv: "Platform fee (annual)",
  usage_acv: "Usage value (annual)",
  term_months: "Term (months)",
  quantity: "Quantity",
  rep_id: "Rep",
  approved_by: "Approved by",
  competitor_present: "Competitor in deal",
  lost_reason: "Lost reason",
};

const CONF_COLOR: Record<Confidence, string> = {
  high: "border-teal/40 text-teal",
  medium: "border-amber/40 text-amber",
  low: "border-coral/40 text-coral",
  none: "border-border text-muted",
};

// --- presentation helpers ---------------------------------------------------

function MetricCard({
  label, value, sub, accent,
}: { label: string; value: string; sub?: string; accent?: "navy" | "coral" }) {
  return (
    <div className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
      <div className="text-sm text-muted">{label}</div>
      <div className={`mt-1 text-3xl font-bold tabular-nums ${accent === "coral" ? "text-coral" : "text-fg"}`}>
        {value}
      </div>
      {sub ? <div className="mt-1 text-sm text-muted">{sub}</div> : null}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

// --- results view (uploaded data) ------------------------------------------

function Results({ d }: { d: Diagnostic }) {
  const { overview: o, leakage: l } = d;
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Booked value (annual)" value={money(o.booked_acv_won)} />
        <MetricCard
          label="Price realization"
          value={pct(o.price_realization_won)}
          sub={`Average discount ${pct(o.avg_discount_won)}`}
        />
        <MetricCard
          label="Pricing upside to pursue"
          value={money(l.excess_vs_reference_won)}
          sub={`${pct(l.excess_pct_of_booked)} of booked value, past the win point`}
          accent="coral"
        />
        <MetricCard
          label="Win rate"
          value={pct(o.win_rate)}
          sub={`${o.won.toLocaleString()} won, ${o.lost.toLocaleString()} lost`}
        />
      </section>

      <Card title="Win rate vs discount">
        <WinRateChart bands={d.win_rate_by_band} reference={d.reference_discount} />
      </Card>

      {d.realization_by_segment?.length ? (
        <Card title="Price realization by segment">
          <SegmentChart rows={d.realization_by_segment} />
        </Card>
      ) : null}

      {Object.entries(d.hierarchy_slices ?? {}).map(([dim, rows]) => {
        const labels: Record<string, string> = {
          business_unit: "business unit",
          product_line: "product line",
          product_family: "product family",
          sku: "SKU",
        };
        return rows.length ? (
          <Card key={dim} title={`Price realization by ${labels[dim] ?? dim}`}>
            <SegmentChart rows={rows} dimKey={dim} />
          </Card>
        ) : null;
      })}

      <Card title="Where the money goes">
        <LeakageBars leakage={l} />
      </Card>

      {d.top_leak_deals?.length ? (
        <Card title="Deals to look at first">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-mist text-left text-muted">
                  <th className="py-2 pr-4 font-medium">Account</th>
                  <th className="py-2 pr-4 font-medium">Segment</th>
                  <th className="py-2 pr-4 text-right font-medium">List value</th>
                  <th className="py-2 pr-4 text-right font-medium">Discount</th>
                  <th className="py-2 pr-4 text-right font-medium">Beyond win point</th>
                </tr>
              </thead>
              <tbody>
                {d.top_leak_deals.slice(0, 8).map((r) => (
                  <tr key={r.opportunity_id} className="border-b border-mist/60">
                    <td className="py-2 pr-4 font-medium text-fg">{r.resolved_account_name}</td>
                    <td className="py-2 pr-4 text-muted">{r.segment}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{money(r.list_acv)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{pct(r.discount_pct)}</td>
                    <td className="py-2 pr-4 text-right font-semibold tabular-nums text-coral">
                      {money(r.excess_discount_dollars)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}

// --- mapping review --------------------------------------------------------

function MappingReview({
  map,
  onMappingChange,
  onBack,
  onRun,
  busy,
  error,
}: {
  map: MapResponse;
  onMappingChange: (m: Record<string, string | null>) => void;
  onBack: () => void;
  onRun: () => void;
  busy: boolean;
  error: string;
}) {
  const mapping = map.mapping;
  // Which headers are claimed by which field (to grey out duplicates).
  const claimedBy = useMemo(() => {
    const out: Record<string, string> = {};
    for (const [f, h] of Object.entries(mapping)) if (h) out[h] = f;
    return out;
  }, [mapping]);

  const missingRequired = REQUIRED_FIELDS.filter((f) => !mapping[f]);

  const fields = Object.keys(mapping).sort((a, b) => {
    const ra = (REQUIRED_FIELDS as readonly string[]).includes(a) ? 0 : 1;
    const rb = (REQUIRED_FIELDS as readonly string[]).includes(b) ? 0 : 1;
    if (ra !== rb) return ra - rb;
    return (FIELD_LABEL[a] ?? a).localeCompare(FIELD_LABEL[b] ?? b);
  });

  function setField(field: string, header: string | null) {
    const next = { ...mapping };
    // Unclaim if this header was used by another field.
    if (header) {
      for (const f of Object.keys(next)) {
        if (f !== field && next[f] === header) next[f] = null;
      }
    }
    next[field] = header;
    onMappingChange(next);
  }

  const sampleVal = (h: string | null) => {
    if (!h || !map.sample.length) return "";
    const v = map.sample[0][h];
    return v && v.length > 38 ? v.slice(0, 38) + "…" : v ?? "";
  };

  return (
    <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-fg">Review the column mapping</h2>
      <p className="mt-1 text-sm text-muted">
        We matched your headers to our schema (locally — synonyms, fuzzy, and a
        small on-device embedding model). Required fields are marked with{" "}
        <span className="text-coral">*</span>. Override anything that looks
        wrong before running the diagnostic.
      </p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-mist text-left text-muted">
              <th className="py-2 pr-4 font-medium">Our field</th>
              <th className="py-2 pr-4 font-medium">Their column</th>
              <th className="py-2 pr-4 font-medium">Match</th>
              <th className="py-2 pr-4 font-medium">Sample value</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => {
              const required = (REQUIRED_FIELDS as readonly string[]).includes(field);
              const conf = map.confidence[field] ?? "none";
              const current = mapping[field];
              return (
                <tr key={field} className="border-b border-mist/60">
                  <td className="py-2 pr-4">
                    <span className="font-medium text-fg">{FIELD_LABEL[field] ?? field}</span>
                    {required ? <span className="ml-1 text-coral">*</span> : null}
                    <div className="text-xs text-muted">{field}</div>
                  </td>
                  <td className="py-2 pr-4">
                    <select
                      value={current ?? ""}
                      onChange={(e) => setField(field, e.target.value || null)}
                      className="w-full rounded-lg border border-mist bg-surface-2 px-2 py-1.5 text-sm text-fg focus:border-teal focus:outline-none"
                    >
                      <option value="">— none —</option>
                      {map.headers.map((h) => {
                        const taken = claimedBy[h] && claimedBy[h] !== field;
                        return (
                          <option key={h} value={h}>
                            {h}{taken ? ` (used by ${claimedBy[h]})` : ""}
                          </option>
                        );
                      })}
                    </select>
                  </td>
                  <td className="py-2 pr-4">
                    {current ? (
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${CONF_COLOR[conf]}`}>
                        {conf}
                        {map.used[current] ? ` · ${map.used[current]}` : ""}
                      </span>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-xs text-muted font-mono">{sampleVal(current)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {missingRequired.length ? (
        <p className="mt-3 text-sm text-coral">
          Required field{missingRequired.length > 1 ? "s" : ""} not yet mapped:{" "}
          {missingRequired.map((f) => FIELD_LABEL[f] ?? f).join(", ")}.
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-coral">{error}</p> : null}

      <div className="mt-4 flex gap-3">
        <button
          onClick={onBack}
          className="rounded-lg border border-mist bg-surface px-4 py-2 text-sm font-medium text-fg hover:border-teal"
        >
          ← Back
        </button>
        <button
          onClick={onRun}
          disabled={busy || missingRequired.length > 0}
          className="rounded-lg bg-navy px-5 py-2 font-medium text-white transition hover:bg-navy/90 disabled:opacity-50"
        >
          {busy ? "Analyzing…" : "Run the diagnostic"}
        </button>
      </div>
    </section>
  );
}

// --- root client ------------------------------------------------------------

export default function UploadClient() {
  const [file, setFile] = useState<File | null>(null);
  const [map, setMap] = useState<MapResponse | null>(null);
  const [mapping, setMapping] = useState<Record<string, string | null> | null>(null);
  const [res, setRes] = useState<Diagnostic | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function readFile() {
    if (!file) return;
    setBusy(true);
    setError("");
    setRes(null);
    setMap(null);
    setMapping(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch("/api/map-headers", { method: "POST", body: fd });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.error || "Could not read that file.");
      }
      const data: MapResponse = await r.json();
      setMap(data);
      setMapping(data.mapping);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read that file.");
    } finally {
      setBusy(false);
    }
  }

  async function runDiagnostic() {
    if (!file || !mapping) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("mapping_json", JSON.stringify(mapping));
      const r = await fetch("/api/diagnostic", { method: "POST", body: fd });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.error || "Analysis failed.");
      }
      setRes(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {!res ? (
        <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="file"
              accept=".csv,.xlsx,.xls,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setMap(null);
                setMapping(null);
                setRes(null);
                setError("");
              }}
              className="text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-mist file:px-4 file:py-2 file:text-sm file:font-medium file:text-fg"
            />
            <button
              onClick={readFile}
              disabled={!file || busy}
              className="rounded-lg bg-navy px-5 py-2.5 font-medium text-white transition hover:bg-navy/90 disabled:opacity-50"
            >
              {busy && !map ? "Reading…" : map ? "Re-read file" : "Read file"}
            </button>
          </div>
          {error && !map ? <p className="mt-3 text-sm text-coral">{error}</p> : null}
          <p className="mt-3 text-xs text-muted">
            CSV or Excel. Processed in memory to produce the analysis; not stored.
          </p>
        </section>
      ) : null}

      {map && mapping && !res ? (
        <MappingReview
          map={{ ...map, mapping }}
          onMappingChange={setMapping}
          onBack={() => { setMap(null); setMapping(null); setError(""); }}
          onRun={runDiagnostic}
          busy={busy}
          error={error}
        />
      ) : null}

      {res ? <Results d={res} /> : null}
    </div>
  );
}
