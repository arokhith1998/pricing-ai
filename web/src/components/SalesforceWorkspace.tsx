"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import CompetitorContextPanel from "@/components/CompetitorContextPanel";
import Reveal from "@/components/Reveal";

type Connection = {
  org_id: string;
  instance_url: string;
  status: string;
  last_error: string;
  last_sync_at: string | null;
  last_sync_closed: number;
  last_sync_open: number;
};

type Field = { name: string; label: string; type: string; custom: boolean };
type MappingFields = {
  list_value_field: string;
  booked_value_field: string;
  segment_field: string;
  product_field: string;
  value_metric_field: string;
  competitor_field: string;
  approved_by_field: string;
  term_months_field: string;
};
type MappingConfig = {
  mapping: MappingFields;
  policy_threshold_pct: number;
  default_value_metric: "seats" | "consumption" | "hybrid";
};

type Readiness = {
  records_fetched: number;
  closed_usable: number;
  open_usable: number;
  blockers: string[];
  warnings: string[];
  currencies: string[];
  list_source?: "mapped_field" | "line_items" | "none";
};

type Guidance = {
  opportunity_id: string;
  account: string;
  segment: string;
  product_tier: string;
  rep_id: string;
  close_date: string;
  currency_iso: string;
  salesforce_url: string;
  list_acv: number;
  quoted_acv: number;
  current_discount: number;
  recommended_discount: number;
  policy_threshold: number;
  reference_discount: number;
  reference_basis: string;
  below_guardrail: boolean;
  price_to_retain: number;
  win_rate_at_current_band: number;
  win_rate_at_recommended_band: number;
  current_band_deals: number;
  recommended_band_deals: number;
  competitor_present: boolean;
  caveat: string;
  evidence_source?: string;
  comparables: Array<{
    opportunity_id: string;
    resolved_account_name: string;
    segment: string;
    list_acv: number;
    discount_pct: number;
    is_won: boolean;
  }>;
};

type ValueMetricReference = {
  value_metric: string;
  deals: number;
  bands_populated: number;
  reference_threshold: number;
  reference_band: string;
  basis: string;
};

type Analysis = {
  overview: {
    opportunities: number;
    won: number;
    lost: number;
    win_rate: number;
    booked_acv_won: number;
    price_realization_won: number;
    avg_discount_won: number;
  };
  leakage: {
    reference_threshold: number;
    excess_vs_segment_reference_won: number;
    deals_above_segment_reference: number;
    off_policy_leakage_won: number;
  };
  governance: {
    off_policy_won: number;
    off_policy_unapproved_won: number;
    unapproved_discount_dollars: number;
  };
  win_rate_by_band: Array<{
    discount_band: string;
    deals: number;
    won: number;
    win_rate: number;
  }>;
  realization_by_segment: Array<{
    segment: string;
    deals: number;
    avg_discount: number;
    price_realization: number;
    booked_acv: number;
  }>;
  top_leak_deals: Array<{
    opportunity_id: string;
    resolved_account_name: string;
    segment: string;
    discount_pct: number;
    excess_discount_dollars: number;
  }>;
  // Per-value-metric reference discount partition (CONTRACT C). Optional so
  // an org running against an older cached backend still renders.
  value_metric_reference?: ValueMetricReference[];
};

type Workspace = {
  connection: Connection;
  mapping: MappingConfig;
  source_readiness: Readiness;
  analysis: Analysis | null;
  guidance: Guidance[];
  synced_at: string;
  outcomes_reconciled: number;
};

type WorkflowItem = {
  id: string;
  deal_id: string;
  event: string;
  account: string;
  actor: string;
  justification: string;
  created_at: string;
  verdict?: { requested_pct?: number };
};

const EMPTY_MAPPING: MappingConfig = {
  mapping: {
    list_value_field: "",
    booked_value_field: "Amount",
    segment_field: "",
    product_field: "",
    value_metric_field: "",
    competitor_field: "",
    approved_by_field: "",
    term_months_field: "",
  },
  policy_threshold_pct: 15,
  default_value_metric: "hybrid",
};

function money(value: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function Metric({ label, value, note, accent = false }: {
  label: string; value: string; note: string; accent?: boolean;
}) {
  return (
    <div className={`rounded-xl border p-4 ${accent ? "border-coral/40 bg-coral/5" : "border-mist bg-surface"}`}>
      <div className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${accent ? "text-coral" : "text-fg"}`}>{value}</div>
      <div className="mt-1 text-xs text-slate">{note}</div>
    </div>
  );
}

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status}).`);
  return body;
}

export default function SalesforceWorkspace({
  oauthConnected,
  oauthError,
}: {
  oauthConnected: boolean;
  oauthError: string;
}) {
  const [configured, setConfigured] = useState(false);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [fields, setFields] = useState<Field[]>([]);
  const [mapping, setMapping] = useState<MappingConfig>(EMPTY_MAPPING);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowItem[]>([]);
  const [tab, setTab] = useState<"executive" | "pricing" | "deals">("executive");
  const [selectedId, setSelectedId] = useState("");
  const [actor, setActor] = useState("");
  const [requested, setRequested] = useState("");
  const [justification, setJustification] = useState("");
  const [writeback, setWriteback] = useState(true);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(
    oauthConnected ? "Salesforce connected. Review the mapping, then sync." : "",
  );

  useEffect(() => {
    let active = true;
    jsonFetch<{
      configured: boolean;
      connected: boolean;
      connection: Connection | null;
    }>("/api/salesforce/connection")
      .then(async (result) => {
        if (!result.connection) return { result, setup: null };
        const [metadata, saved, log] = await Promise.all([
          jsonFetch<{ fields: Field[] }>("/api/salesforce/metadata"),
          jsonFetch<{ mapping: MappingConfig }>("/api/salesforce/mapping"),
          jsonFetch<{ items: WorkflowItem[] }>("/api/salesforce/workflow"),
        ]);
        return { result, setup: { metadata, saved, log } };
      })
      .then(({ result, setup }) => {
        if (!active) return;
        setConfigured(result.configured);
        setConnection(result.connection);
        if (setup) {
          setFields(setup.metadata.fields);
          setMapping(setup.saved.mapping);
          setWorkflow(setup.log.items);
        }
      })
      .catch((cause) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Could not load Salesforce.");
        }
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const selected = useMemo(
    () => workspace?.guidance.find((deal) => deal.opportunity_id === selectedId) ?? null,
    [workspace, selectedId],
  );
  const accessDenied = /access code required|sign in at \/login/i.test(error);

  async function saveMapping() {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await jsonFetch<{ mapping: MappingConfig }>("/api/salesforce/mapping", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mapping),
      });
      setMapping(result.mapping);
      setNotice("Field mapping saved.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save mapping.");
    } finally { setBusy(false); }
  }

  async function sync() {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await jsonFetch<Workspace>("/api/salesforce/workspace");
      setWorkspace(result);
      setConnection(result.connection);
      if (result.guidance.length) {
        setSelectedId(result.guidance[0].opportunity_id);
        setRequested((result.guidance[0].current_discount * 100).toFixed(1));
      }
      const log = await jsonFetch<{ items: WorkflowItem[] }>("/api/salesforce/workflow");
      setWorkflow(log.items);
      setNotice(
        result.source_readiness.blockers.length
          ? "Sync completed, but data-readiness blockers must be fixed before analysis."
          : `Live Salesforce analysis refreshed${result.outcomes_reconciled ? `; ${result.outcomes_reconciled} deal outcome${result.outcomes_reconciled === 1 ? "" : "s"} reconciled` : ""}.`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Salesforce sync failed.");
    } finally { setBusy(false); }
  }

  async function disconnect() {
    if (!window.confirm("Disconnect this Salesforce org from Pricekeel?")) return;
    setBusy(true); setError("");
    try {
      await jsonFetch("/api/salesforce/connection", { method: "DELETE" });
      setConnection(null); setWorkspace(null); setWorkflow([]);
      setNotice("Salesforce disconnected and local tokens removed.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not disconnect Salesforce.");
    } finally { setBusy(false); }
  }

  async function act(
    event: "accepted" | "override_requested" | "approved" | "rejected",
    dealId?: string,
  ) {
    const targetId = dealId ?? selected?.opportunity_id ?? "";
    if (!targetId || !actor.trim()) {
      setError("Select a deal and enter the person taking the action.");
      return;
    }
    // Approve and reject decide the terms already on record. Sending a
    // discount with them would overwrite what the rep actually requested.
    const decidesOverride = event === "approved" || event === "rejected";
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await jsonFetch<{ writeback: { requested: boolean; success: boolean; error: string; audit_error: string } }>(
        "/api/salesforce/workflow",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            deal_id: targetId,
            event,
            actor: actor.trim(),
            justification,
            requested_discount_pct:
              decidesOverride || !requested ? undefined : Number(requested),
            writeback,
          }),
        },
      );
      const log = await jsonFetch<{ items: WorkflowItem[] }>("/api/salesforce/workflow");
      setWorkflow(log.items);
      if (result.writeback.audit_error) setError(result.writeback.audit_error);
      setNotice(
        result.writeback.requested
          ? result.writeback.success
            ? "Decision logged in Pricekeel and written to Salesforce as a completed Task."
            : result.writeback.error
          : "Decision logged in Pricekeel.",
      );
      setJustification("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Workflow action failed.");
    } finally { setBusy(false); }
  }

  function setMap(key: keyof MappingFields, value: string) {
    setMapping((current) => ({
      ...current,
      mapping: { ...current.mapping, [key]: value },
    }));
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <Reveal>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-teal">CRM workflow</div>
            <h1 className="mt-2 text-3xl font-bold text-fg">Salesforce pricing desk</h1>
            <p className="mt-2 max-w-3xl text-slate">
              Live discount intelligence on Opportunity history, with a human approval loop and an append-only decision record.
            </p>
          </div>
          {connection ? (
            <div className="rounded-xl border border-teal/30 bg-teal/5 px-4 py-3 text-sm">
              <div className="font-semibold text-fg">Connected · org {connection.org_id}</div>
              <div className="mt-1 text-xs text-muted">{connection.instance_url}</div>
            </div>
          ) : null}
        </div>
      </Reveal>

      {oauthError ? <div className="rounded-lg border border-coral/40 bg-coral/5 p-3 text-sm text-coral">Salesforce authorization failed ({oauthError.replaceAll("_", " ")}). Try connecting again.</div> : null}
      {error && !accessDenied ? <div role="alert" className="rounded-lg border border-coral/40 bg-coral/5 p-3 text-sm text-coral">{error}</div> : null}
      {notice ? <div role="status" className="rounded-lg border border-teal/40 bg-teal/5 p-3 text-sm text-fg">{notice}</div> : null}

      {!connection && accessDenied ? (
        <Reveal>
          <section className="rounded-2xl border border-mist bg-surface p-6">
            <h2 className="text-xl font-semibold text-fg">Sign in to your customer workspace</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate">
              Your access code selects the customer tenant and its Salesforce connection. Sign in before connecting, mapping, or refreshing an org.
            </p>
            <Link href="/login" className="mt-5 inline-flex rounded-lg bg-teal px-5 py-2.5 text-sm font-semibold text-bg">
              Sign in
            </Link>
          </section>
        </Reveal>
      ) : !connection ? (
        <Reveal>
          <section className="rounded-2xl border border-mist bg-surface p-6">
            <h2 className="text-xl font-semibold text-fg">Connect a Salesforce org</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate">
              Pricekeel requests API and offline access through Salesforce OAuth. Tokens stay server-side and encrypted. Opportunity rows are analyzed in memory and are not copied into a Pricekeel CRM table.
            </p>
            {!configured ? (
              <div className="mt-4 rounded-lg border border-coral/30 bg-coral/5 p-3 text-sm text-coral">
                The Salesforce External Client App environment variables are not configured on this deployment yet.
              </div>
            ) : null}
            <a href="/api/salesforce/oauth/start" className={`mt-5 inline-flex rounded-lg bg-teal px-5 py-2.5 text-sm font-semibold text-bg ${!configured ? "pointer-events-none opacity-50" : ""}`}>
              Connect Salesforce
            </a>
          </section>
        </Reveal>
      ) : (
        <>
          <Reveal>
            <details className="rounded-xl border border-mist bg-surface p-5">
              <summary className="cursor-pointer font-semibold text-fg">Connection and field mapping</summary>
              <p className="mt-2 text-sm text-slate">
                Map each field to your Salesforce source. The list value must be a true pre-discount (annualized list) price. Leave it blank only if your Opportunity Products carry real list prices: a list value that equals the booked amount makes discount and leakage read as zero and will block analysis. Other blank mappings fall back to standard fields or an explicit default.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {([
                  ["list_value_field", "Annualized list value"],
                  ["booked_value_field", "Booked / quoted ACV"],
                  ["segment_field", "Customer segment"],
                  ["product_field", "Product / package"],
                  ["value_metric_field", "Value metric"],
                  ["competitor_field", "Competitor present"],
                  ["approved_by_field", "Discount approver"],
                  ["term_months_field", "Term months"],
                ] as Array<[keyof MappingFields, string]>).map(([key, label]) => (
                  <label key={key} className="text-xs font-semibold uppercase tracking-wider text-muted">
                    {label}
                    <select value={mapping.mapping[key]} onChange={(event) => setMap(key, event.target.value)} className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal normal-case tracking-normal text-ink">
                      <option value="">{key === "list_value_field" ? "Opportunity Products (true list prices)" : "Standard fallback / none"}</option>
                      {fields.map((field) => <option key={field.name} value={field.name}>{field.label} · {field.name}</option>)}
                    </select>
                    {key === "list_value_field" ? <span className="mt-1 block text-[10px] font-normal normal-case tracking-normal text-muted">Pre-discount list, not the sell price.</span> : null}
                  </label>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap items-end gap-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">Policy threshold (%)<input type="number" min="0" max="40" step="0.5" value={mapping.policy_threshold_pct} onChange={(event) => setMapping((current) => ({ ...current, policy_threshold_pct: Number(event.target.value) }))} className="mt-1 block w-36 rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal text-ink" /></label>
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">Default value metric<select value={mapping.default_value_metric} onChange={(event) => setMapping((current) => ({ ...current, default_value_metric: event.target.value as MappingConfig["default_value_metric"] }))} className="mt-1 block rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal normal-case text-ink"><option value="hybrid">Hybrid</option><option value="seats">Seats</option><option value="consumption">Consumption</option></select></label>
                <button type="button" disabled={busy} onClick={saveMapping} className="rounded-lg border border-teal px-4 py-2 text-sm font-semibold text-teal disabled:opacity-50">Save mapping</button>
                <button type="button" disabled={busy} onClick={disconnect} className="ml-auto rounded-lg border border-coral/40 px-4 py-2 text-sm font-semibold text-coral disabled:opacity-50">Disconnect</button>
              </div>
            </details>
          </Reveal>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-slate">{connection.last_sync_at ? `Last live sync ${new Date(connection.last_sync_at).toLocaleString()} · ${connection.last_sync_closed} closed / ${connection.last_sync_open} open` : "No live analysis has run yet."}</div>
            <button type="button" onClick={sync} disabled={busy} className="rounded-lg bg-teal px-5 py-2.5 text-sm font-semibold text-bg disabled:opacity-50">{busy ? "Working…" : "Refresh from Salesforce"}</button>
          </div>

          {workspace ? <ReadinessPanel readiness={workspace.source_readiness} /> : null}

          {workspace?.analysis ? (
            <>
              <div className="flex gap-1 rounded-xl border border-mist bg-surface p-1">
                {(["executive", "pricing", "deals"] as const).map((value) => <button key={value} type="button" onClick={() => setTab(value)} className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold capitalize ${tab === value ? "bg-navy text-white" : "text-slate hover:text-fg"}`}>{value === "deals" ? "Deal desk" : value}</button>)}
              </div>
              {tab === "executive" ? <Executive analysis={workspace.analysis} guidance={workspace.guidance} workflow={workflow} /> : null}
              {tab === "pricing" ? <div className="space-y-5"><Pricing analysis={workspace.analysis} /><CompetitorContextPanel /></div> : null}
              {tab === "deals" ? <DealDesk guidance={workspace.guidance} selected={selected} selectedId={selectedId} setSelectedId={setSelectedId} actor={actor} setActor={setActor} requested={requested} setRequested={setRequested} justification={justification} setJustification={setJustification} writeback={writeback} setWriteback={setWriteback} busy={busy} act={act} workflow={workflow} instanceUrl={workspace.connection.instance_url} /> : null}
            </>
          ) : null}
        </>
      )}
    </main>
  );
}

function ReadinessPanel({ readiness }: { readiness: Readiness }) {
  return <section className="rounded-xl border border-mist bg-surface p-4"><div className="flex flex-wrap gap-4 text-sm"><span><strong className="text-fg">{readiness.closed_usable}</strong> usable closed</span><span><strong className="text-fg">{readiness.open_usable}</strong> usable open</span><span><strong className="text-fg">{readiness.currencies.join(", ") || "org default"}</strong> currency</span>{readiness.list_source ? <span><strong className="text-fg">{readiness.list_source === "mapped_field" ? "mapped list field" : readiness.list_source === "line_items" ? "line-item list" : "no list source"}</strong> list basis</span> : null}</div>{readiness.blockers.map((item) => <div key={item} className="mt-2 text-sm text-coral">Blocker: {item}</div>)}{readiness.warnings.map((item) => <div key={item} className="mt-2 text-sm text-amber-300">Check: {item}</div>)}</section>;
}

function Executive({ analysis, guidance, workflow }: { analysis: Analysis; guidance: Guidance[]; workflow: WorkflowItem[] }) {
  const currency = guidance[0]?.currency_iso || "USD";
  const flagged = guidance.filter((deal) => !deal.below_guardrail);
  return <section className="space-y-5"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Metric label="Price realization" value={pct(analysis.overview.price_realization_won)} note={`${analysis.overview.won.toLocaleString()} won opportunities`} /><Metric label="Win rate" value={pct(analysis.overview.win_rate)} note={`${analysis.overview.opportunities.toLocaleString()} closed outcomes`} /><Metric label="Open exceptions" value={flagged.length.toLocaleString()} note="Open deals above their reference guardrail" accent={flagged.length > 0} /><Metric label="Price to retain" value={money(flagged.reduce((sum, deal) => sum + deal.price_to_retain, 0), currency)} note="If flagged deals move to the disclosed guardrail" accent /></div><div className="grid gap-4 lg:grid-cols-2"><section className="rounded-xl border border-mist bg-surface p-5"><h2 className="font-semibold text-fg">Win rate by discount band</h2><div className="mt-4 space-y-3">{analysis.win_rate_by_band.map((row) => <div key={row.discount_band}><div className="flex justify-between text-xs text-slate"><span>{row.discount_band} · {row.deals} deals</span><span>{pct(row.win_rate)}</span></div><div className="mt-1 h-2 rounded bg-surface-2"><div className="h-2 rounded bg-teal" style={{ width: `${Math.max(2, row.win_rate * 100)}%` }} /></div></div>)}</div></section><section className="rounded-xl border border-mist bg-surface p-5"><h2 className="font-semibold text-fg">Workflow pulse</h2><div className="mt-4 text-3xl font-bold text-fg">{workflow.length}</div><p className="text-sm text-slate">Pricing actions logged in the current tenant.</p><div className="mt-4 text-sm text-slate">Reference threshold: <strong className="text-fg">{pct(analysis.leakage.reference_threshold)}</strong></div><div className="mt-1 text-sm text-slate">Historical excess to investigate: <strong className="text-fg">{money(analysis.leakage.excess_vs_segment_reference_won, currency)}</strong></div>{analysis.value_metric_reference && analysis.value_metric_reference.length >= 2 ? <div className="mt-3 border-t border-mist pt-3"><div className="text-xs font-semibold uppercase tracking-wider text-muted">Reference discount by value metric</div><div className="mt-2 space-y-1">{analysis.value_metric_reference.map((row) => <div key={row.value_metric} className="flex items-baseline justify-between gap-3 text-xs text-slate"><span className="font-medium text-ink">{row.value_metric}</span><span className="tabular-nums">{row.reference_band} ({pct(row.reference_threshold)}) · {row.basis}</span></div>)}</div></div> : null}</section></div></section>;
}

function Pricing({ analysis }: { analysis: Analysis }) {
  return <section className="grid gap-5 lg:grid-cols-2"><div className="rounded-xl border border-mist bg-surface p-5"><h2 className="font-semibold text-fg">Realization by segment</h2><div className="mt-3 overflow-x-auto"><table className="w-full text-sm"><thead className="text-left text-xs uppercase tracking-wider text-muted"><tr><th className="py-2">Segment</th><th className="text-right">Deals</th><th className="text-right">Discount</th><th className="text-right">Realization</th></tr></thead><tbody>{analysis.realization_by_segment.map((row) => <tr key={row.segment} className="border-t border-mist"><td className="py-2 text-fg">{row.segment}</td><td className="text-right">{row.deals}</td><td className="text-right">{pct(row.avg_discount)}</td><td className="text-right">{pct(row.price_realization)}</td></tr>)}</tbody></table></div></div><div className="rounded-xl border border-mist bg-surface p-5"><h2 className="font-semibold text-fg">Deals to investigate</h2><div className="mt-3 space-y-2">{analysis.top_leak_deals.slice(0, 8).map((row) => <div key={row.opportunity_id} className="flex items-center justify-between gap-3 rounded-lg bg-surface-2 p-3 text-sm"><div><div className="font-medium text-fg">{row.resolved_account_name}</div><div className="text-xs text-muted">{row.segment} · {pct(row.discount_pct)} discount</div></div><div className="font-semibold tabular-nums text-coral">{money(row.excess_discount_dollars)}</div></div>)}</div></div></section>;
}

function DealDesk(props: { guidance: Guidance[]; selected: Guidance | null; selectedId: string; setSelectedId: (value: string) => void; actor: string; setActor: (value: string) => void; requested: string; setRequested: (value: string) => void; justification: string; setJustification: (value: string) => void; writeback: boolean; setWriteback: (value: boolean) => void; busy: boolean; act: (event: "accepted" | "override_requested" | "approved" | "rejected", dealId?: string) => void; workflow: WorkflowItem[]; instanceUrl: string }) {
  const { selected } = props;
  const latestEvent = props.workflow.find((item) => item.deal_id === props.selectedId)?.event ?? "";
  const approvalPending = latestEvent === "override_requested";
  // An override outlives the open-deal list whenever the opportunity closes or
  // the org drops below the evidence floor: the deal stops being returned as
  // guidance, so its panel disappears and the pending request becomes
  // unreachable. The request still stands, so surface those separately.
  const openIds = new Set(props.guidance.map((deal) => deal.opportunity_id));
  const latestByDeal = new Map<string, WorkflowItem>();
  for (const item of props.workflow) {
    if (!latestByDeal.has(item.deal_id)) latestByDeal.set(item.deal_id, item);
  }
  const pendingOffList = [...latestByDeal.values()].filter(
    (item) => item.event === "override_requested" && !openIds.has(item.deal_id),
  );
  return <section className="space-y-5"><div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]"><div className="rounded-xl border border-mist bg-surface p-4"><h2 className="font-semibold text-fg">Open opportunities</h2><div className="mt-3 max-h-[580px] space-y-2 overflow-y-auto">{props.guidance.length ? props.guidance.map((deal) => <button type="button" key={deal.opportunity_id} onClick={() => { props.setSelectedId(deal.opportunity_id); props.setRequested((deal.current_discount * 100).toFixed(1)); }} className={`w-full rounded-lg border p-3 text-left ${props.selectedId === deal.opportunity_id ? "border-teal bg-teal/5" : "border-mist bg-surface-2"}`}><div className="flex justify-between gap-3"><span className="font-medium text-fg">{deal.account}</span><span className={deal.below_guardrail ? "text-teal" : "text-coral"}>{deal.below_guardrail ? "within" : "exception"}</span></div><div className="mt-1 text-xs text-muted">{deal.segment} · {pct(deal.current_discount)} requested · close {deal.close_date}</div></button>) : <p className="text-sm text-slate">No usable open opportunities were returned.</p>}</div></div>{selected ? <div className="rounded-xl border border-mist bg-surface p-5"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-xl font-semibold text-fg">{selected.account}</h2><p className="text-sm text-slate">{selected.product_tier} · {selected.segment} · {selected.rep_id}{latestEvent ? ` · latest: ${latestEvent.replaceAll("_", " ")}` : ""}</p></div><a href={`${props.instanceUrl}${selected.salesforce_url}`} target="_blank" rel="noreferrer" className="text-sm font-semibold text-teal">Open in Salesforce ↗</a></div><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Requested" value={pct(selected.current_discount)} note={money(selected.quoted_acv, selected.currency_iso)} /><Metric label="Recommended" value={pct(selected.recommended_discount)} note={selected.reference_basis} /><Metric label="Retain" value={money(selected.price_to_retain, selected.currency_iso)} note="At the recommendation" accent={!selected.below_guardrail} /><Metric label="Evidence" value={`${selected.recommended_band_deals}`} note={`historical deals in the recommended band`} /></div>{selected.competitor_present ? <div className="mt-4 rounded-lg border border-amber-300/30 bg-amber-300/5 p-3 text-sm text-amber-200">A competitor is recorded on this opportunity. Treat it as context, not an automatic reason to move the guardrail. <Link href="/competitor-watch" className="font-semibold underline">Review sourced competitor evidence</Link>.</div> : null}<p className="mt-4 text-xs text-muted"><span className="font-semibold text-slate">Method: correlational band guardrail from your closed book, not the modeled EV curve shown in the sample. </span>{selected.caveat}</p><div className="mt-5 grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold uppercase tracking-wider text-muted">Actor<input value={props.actor} onChange={(event) => props.setActor(event.target.value)} placeholder="Rep or approver name" className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal normal-case text-ink" /></label><label className="text-xs font-semibold uppercase tracking-wider text-muted">Requested discount (%)<input type="number" min="0" max="40" step="0.5" value={props.requested} onChange={(event) => props.setRequested(event.target.value)} className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal text-ink" /></label><label className="sm:col-span-2 text-xs font-semibold uppercase tracking-wider text-muted">Justification<textarea rows={3} value={props.justification} onChange={(event) => props.setJustification(event.target.value)} placeholder="Required for an override; preserve the commercial context." className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal normal-case text-ink" /></label></div><label className="mt-3 flex items-center gap-2 text-sm text-slate"><input type="checkbox" checked={props.writeback} onChange={(event) => props.setWriteback(event.target.checked)} /> Write a completed Task to this Salesforce Opportunity</label><div className="mt-4 flex flex-wrap gap-2"><button disabled={props.busy} onClick={() => props.act("accepted")} className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50">Accept recommendation</button><button disabled={props.busy} onClick={() => props.act("override_requested")} className="rounded-lg border border-coral/50 px-4 py-2 text-sm font-semibold text-coral disabled:opacity-50">Request override</button><button disabled={props.busy || !approvalPending} onClick={() => props.act("approved")} title={approvalPending ? "Approve the pending override" : "An override request is required first"} className="rounded-lg border border-teal/50 px-4 py-2 text-sm font-semibold text-teal disabled:opacity-50">Approve</button><button disabled={props.busy || !approvalPending} onClick={() => props.act("rejected")} title={approvalPending ? "Reject the pending override" : "An override request is required first"} className="rounded-lg border border-mist px-4 py-2 text-sm font-semibold text-slate disabled:opacity-50">Reject</button></div></div> : null}</div>{pendingOffList.length ? <div className="rounded-xl border border-coral/40 bg-surface p-5"><h2 className="font-semibold text-fg">Overrides awaiting a decision, no longer in the open set</h2><p className="mt-1 text-sm text-slate">These opportunities left the open-deal list, usually because they closed in Salesforce. The recorded request stands, and the decision is made on the terms as they were requested.</p><label className="mt-3 block text-xs font-semibold uppercase tracking-wider text-muted">Actor<input value={props.actor} onChange={(event) => props.setActor(event.target.value)} placeholder="Approver name" className="mt-1 w-full max-w-sm rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm font-normal normal-case text-ink" /></label><div className="mt-3 space-y-2">{pendingOffList.map((item) => <div key={item.deal_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface-2 p-3 text-sm"><div><span className="text-fg">{item.account || item.deal_id}</span><span className="text-muted"> · {(item.verdict?.requested_pct ?? 0).toFixed(1)}% requested by {item.actor}{item.justification ? ` · ${item.justification}` : ""}</span></div><div className="flex gap-2"><button type="button" disabled={props.busy} onClick={() => props.act("approved", item.deal_id)} className="rounded-lg border border-teal/50 px-3 py-1.5 text-sm font-semibold text-teal disabled:opacity-50">Approve</button><button type="button" disabled={props.busy} onClick={() => props.act("rejected", item.deal_id)} className="rounded-lg border border-mist px-3 py-1.5 text-sm font-semibold text-slate disabled:opacity-50">Reject</button></div></div>)}</div></div> : null}<div className="rounded-xl border border-mist bg-surface p-5"><h2 className="font-semibold text-fg">Append-only decision history</h2><div className="mt-3 space-y-2">{props.workflow.slice(0, 20).map((item) => <div key={item.id} className="grid gap-1 rounded-lg bg-surface-2 p-3 text-sm sm:grid-cols-[150px_1fr_auto]"><div className="font-semibold text-teal">{item.event.replaceAll("_", " ")}</div><div><span className="text-fg">{item.account || item.deal_id}</span><span className="text-muted"> · {item.actor}{item.justification ? ` · ${item.justification}` : ""}</span></div><time className="text-xs text-muted">{new Date(item.created_at).toLocaleString()}</time></div>)}</div></div></section>;
}
