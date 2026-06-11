"use client";

// The decision log: every approval and exception request, with the verdict it
// received. Receipts styling, numbers sit still. Refetches when the control
// above logs a new decision (DECISION_LOGGED_EVENT) so the receipt appears
// without a reload.

import { useCallback, useEffect, useState } from "react";
import type { ExceptionRecord } from "@/lib/api";
import { money, pct100 } from "@/lib/format";
import { DECISION_LOGGED_EVENT } from "@/components/DecisionControl";

const fmtWhen = (iso: string) =>
  new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

function FloorChip({ below }: { below: boolean }) {
  return (
    <span
      className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${
        below ? "border-coral/40 text-coral" : "border-green/40 text-green"
      }`}
    >
      {below ? "below floor" : "within policy"}
    </span>
  );
}

export default function DecisionLog() {
  const [items, setItems] = useState<ExceptionRecord[] | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    fetch("/api/exceptions?limit=50")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data: { items: ExceptionRecord[] }) => {
        setItems(data.items ?? []);
        setError(false);
      })
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    load();
    window.addEventListener(DECISION_LOGGED_EVENT, load);
    return () => window.removeEventListener(DECISION_LOGGED_EVENT, load);
  }, [load]);

  if (error) {
    return (
      <p className="mt-3 text-sm text-coral">
        Decision log is unavailable. Is the API running?
      </p>
    );
  }

  if (items === null) {
    return <p className="mt-3 text-sm text-slate">Loading the log…</p>;
  }

  if (items.length === 0) {
    return (
      <p className="mt-3 text-sm text-slate">
        No decisions logged yet. Every approval and exception will appear here,
        with its math.
      </p>
    );
  }

  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-mist text-left text-slate">
            <th className="py-1.5 pr-3 font-medium">When</th>
            <th className="py-1.5 pr-3 font-medium">Deal</th>
            <th className="py-1.5 pr-3 text-right font-medium">Requested</th>
            <th className="py-1.5 pr-3 text-right font-medium">Recommended</th>
            <th className="py-1.5 pr-3 text-right font-medium">Floor</th>
            <th className="py-1.5 pr-3 font-medium">Verdict</th>
            <th className="py-1.5 font-medium">Requested by</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r, i) => {
            const v = r.verdict;
            return (
              // The backend's id is not in the list payload per the contract,
              // so key on deal + timestamp + index.
              <tr key={`${r.deal_id}-${r.created_at}-${i}`} className="border-b border-mist/60 align-top">
                <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-slate">
                  {fmtWhen(r.created_at)}
                </td>
                <td className="py-2 pr-3 font-medium text-fg">{r.deal_id}</td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink">
                  {pct100(v.requested_pct)}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink">
                  {pct100(v.recommended_pct)}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink">
                  {pct100(v.floor_pct)}
                </td>
                <td className="py-2 pr-3">
                  <FloorChip below={v.below_floor} />
                  {v.below_floor ? (
                    <div className="mt-1 whitespace-nowrap text-xs tabular-nums text-coral">
                      {money(Math.abs(v.ev_delta_vs_recommended))} EV vs rec
                    </div>
                  ) : null}
                </td>
                <td className="py-2 text-ink">{r.requested_by}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {/* Justification + rationale are the part a CFO actually reads; give
          them a full-width line under the figures instead of a cramped cell. */}
      <ul className="mt-3 space-y-2">
        {items.map((r, i) => (
          <li
            key={`${r.deal_id}-${r.created_at}-${i}-notes`}
            className="rounded-lg border border-mist/60 bg-surface-2 p-3 text-xs leading-relaxed"
          >
            <span className="font-medium text-fg">{r.deal_id}</span>
            <span className="text-slate"> · {fmtWhen(r.created_at)} · {r.requested_by}</span>
            <div className="mt-1 text-ink">
              <span className="text-slate">Justification: </span>
              {r.justification}
            </div>
            <div className="mt-0.5 text-slate">
              <span>Verdict: </span>
              {r.verdict.rationale}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
