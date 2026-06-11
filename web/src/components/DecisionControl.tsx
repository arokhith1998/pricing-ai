"use client";

// The moment the governance loop closes on a deal: approve at the recommended
// discount, or request an exception and have it priced before anyone signs.
// Either way the decision lands in the log with its math. This is a control
// surface, not a contact form: the verdict renders inline and the entry id is
// the receipt.

import { useState } from "react";
import type { ExceptionResult, ExceptionVerdict } from "@/lib/api";
import { money, pct0 } from "@/lib/format";

// DecisionLog listens for this on window and refetches, so a freshly logged
// decision shows up in the log further down the page without a reload.
export const DECISION_LOGGED_EVENT = "pk:decision-logged";

const signedMoney = (x: number) =>
  `${x < 0 ? "-" : "+"}${money(Math.abs(x))}`;

function Verdict({ result }: { result: ExceptionResult }) {
  const v: ExceptionVerdict = result.verdict;
  const when = new Date(result.created_at).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  return (
    <div
      className={`mt-4 rounded-xl border p-4 ${
        v.below_floor ? "border-coral/50 bg-coral/5" : "border-green/40 bg-surface-2"
      }`}
    >
      {v.below_floor ? (
        <>
          <div className="text-sm font-semibold uppercase tracking-wider text-coral">
            Below the floor
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-ink">
            The requested <span className="font-semibold tabular-nums">{pct0(v.requested_pct)}</span>{" "}
            sits below the policy floor of{" "}
            <span className="font-semibold tabular-nums text-coral">{pct0(v.floor_pct)}</span>.
            Versus the recommended {pct0(v.recommended_pct)}, expected value on
            this deal moves{" "}
            <span className="font-semibold tabular-nums text-coral">
              {signedMoney(v.ev_delta_vs_recommended)}
            </span>
            , for a win probability of {pct0(v.win_prob_at_requested)} against{" "}
            {pct0(v.win_prob_at_recommended)} at the recommendation.
          </p>
        </>
      ) : (
        <>
          <div className="text-sm font-semibold uppercase tracking-wider text-green">
            Within policy
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-ink">
            <span className="font-semibold tabular-nums">{pct0(v.requested_pct)}</span>{" "}
            clears the policy floor of {pct0(v.floor_pct)}. Win probability{" "}
            {pct0(v.win_prob_at_requested)} at this discount,{" "}
            {pct0(v.win_prob_at_recommended)} at the recommended{" "}
            {pct0(v.recommended_pct)}.
          </p>
        </>
      )}
      <p className="mt-2 text-sm text-slate">{v.rationale}</p>
      <p className="mt-3 border-t border-mist/60 pt-2.5 text-xs text-slate">
        <span className="font-semibold text-green">Logged.</span> Entry{" "}
        <span className="tabular-nums text-ink">{result.id}</span> · {when} ·
        on the record in the decision log below.
      </p>
    </div>
  );
}

export default function DecisionControl({
  dealId,
  account,
  recommendedDiscount,
}: {
  dealId: string;
  account: string;
  recommendedDiscount: number;
}) {
  const [mode, setMode] = useState<"approve" | "exception" | null>(null);
  const [requestedPct, setRequestedPct] = useState("");
  const [justification, setJustification] = useState("");
  const [requestedBy, setRequestedBy] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ExceptionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(input: {
    requested_discount_pct: number;
    justification: string;
  }) {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/exceptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          deal_id: dealId,
          requested_by: requestedBy.trim(),
          ...input,
        }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        throw new Error(data?.error || "Could not log this decision.");
      }
      setResult((await res.json()) as ExceptionResult);
      window.dispatchEvent(new Event(DECISION_LOGGED_EVENT));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log this decision.");
    } finally {
      setSubmitting(false);
    }
  }

  function onApprove() {
    if (!requestedBy.trim()) {
      setError("Add your name so the log says who approved it.");
      return;
    }
    void submit({
      requested_discount_pct: recommendedDiscount,
      justification: "Approved at the recommended discount.",
    });
  }

  function onRequestException() {
    const parsed = Number(requestedPct);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) {
      setError("Requested discount must be a percentage between 0 and 100.");
      return;
    }
    if (!justification.trim()) {
      setError("A justification is required. It goes on the record.");
      return;
    }
    if (!requestedBy.trim()) {
      setError("Add your name so the log says who requested it.");
      return;
    }
    void submit({
      requested_discount_pct: parsed / 100,
      justification: justification.trim(),
    });
  }

  if (result) {
    return (
      <section className="rounded-xl border border-mist bg-surface p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-fg">Log this decision</h2>
        <p className="mt-1 text-sm text-slate">
          Decision recorded for <span className="text-ink">{account}</span>.
        </p>
        <Verdict result={result} />
        <button
          type="button"
          onClick={() => {
            setResult(null);
            setMode(null);
            setRequestedPct("");
            setJustification("");
          }}
          className="mt-4 rounded-lg border border-mist bg-surface-2 px-3 py-1.5 text-xs font-medium text-fg transition hover:border-teal"
        >
          Log another decision on this deal
        </button>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-teal/40 bg-surface p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-fg">Log this decision</h2>
      <p className="mt-1 text-sm text-slate">
        Every approval and exception on{" "}
        <span className="text-ink">{account}</span> goes on the record with its
        math. Below-floor requests get priced before they get approved.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            setMode("approve");
            setError(null);
          }}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            mode === "approve"
              ? "bg-teal text-bg"
              : "border border-mist bg-surface-2 text-fg hover:border-teal"
          }`}
        >
          Approve at recommended · {pct0(recommendedDiscount)}
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("exception");
            setError(null);
          }}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            mode === "exception"
              ? "bg-coral text-bg"
              : "border border-mist bg-surface-2 text-fg hover:border-coral"
          }`}
        >
          Request exception
        </button>
      </div>

      {mode === "approve" ? (
        <div className="mt-4 space-y-3">
          <div>
            <label htmlFor="dc-approver" className="text-xs font-medium text-slate">
              Approved by
            </label>
            <input
              id="dc-approver"
              type="text"
              value={requestedBy}
              onChange={(e) => setRequestedBy(e.target.value)}
              placeholder="Your name"
              className="mt-1 w-full max-w-xs rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
            />
          </div>
          <button
            type="button"
            onClick={onApprove}
            disabled={submitting}
            className="rounded-lg bg-teal px-4 py-2 text-sm font-medium text-bg transition hover:scale-[1.01] disabled:opacity-60"
          >
            {submitting ? "Logging…" : `Log approval at ${pct0(recommendedDiscount)}`}
          </button>
        </div>
      ) : null}

      {mode === "exception" ? (
        <div className="mt-4 space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="dc-pct" className="text-xs font-medium text-slate">
                Requested discount (%)
              </label>
              <input
                id="dc-pct"
                type="number"
                min={0}
                max={100}
                step="0.5"
                value={requestedPct}
                onChange={(e) => setRequestedPct(e.target.value)}
                placeholder={`Recommended is ${pct0(recommendedDiscount)}`}
                className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm tabular-nums text-ink focus:border-teal focus:outline-none"
              />
            </div>
            <div>
              <label htmlFor="dc-requester" className="text-xs font-medium text-slate">
                Requested by
              </label>
              <input
                id="dc-requester"
                type="text"
                value={requestedBy}
                onChange={(e) => setRequestedBy(e.target.value)}
                placeholder="Your name"
                className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
              />
            </div>
          </div>
          <div>
            <label htmlFor="dc-just" className="text-xs font-medium text-slate">
              Justification (goes on the record)
            </label>
            <textarea
              id="dc-just"
              rows={3}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Why this deal needs more than the recommended discount."
              className="mt-1 w-full rounded-lg border border-mist bg-surface-2 px-3 py-2 text-sm text-ink focus:border-teal focus:outline-none"
            />
          </div>
          <button
            type="button"
            onClick={onRequestException}
            disabled={submitting}
            className="rounded-lg bg-coral px-4 py-2 text-sm font-medium text-bg transition hover:scale-[1.01] disabled:opacity-60"
          >
            {submitting ? "Pricing the request…" : "Price and log this exception"}
          </button>
          <p className="text-xs text-slate">
            The request is priced against the policy floor before it is logged.
            A below-floor verdict does not block it; it makes the cost explicit.
          </p>
        </div>
      ) : null}

      {error ? <p className="mt-3 text-sm text-coral">{error}</p> : null}
    </section>
  );
}
