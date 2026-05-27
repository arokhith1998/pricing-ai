import type { Leakage } from "@/lib/api";
import { money, pct } from "@/lib/format";

// The three leakage lenses, weakest claim to strongest (README + design doc).
// Plain CSS bars scaled to the largest (gross) figure.
export default function LeakageBars({ leakage }: { leakage: Leakage }) {
  const rows = [
    {
      label: "Gross discount given",
      help: "Total list-to-booked giveback. Descriptive, not a problem by itself.",
      value: leakage.gross_discount_won,
      color: "bg-slate",
    },
    {
      label: `Above your discount policy (${pct(leakage.policy_threshold, 0)})`,
      help: "Discount beyond the stated policy threshold. A governance signal.",
      value: leakage.off_policy_leakage_won,
      color: "bg-amber",
    },
    {
      label: "Beyond the win point",
      help: `Discount past ${pct(leakage.reference_threshold, 0)}, where win rate stops improving. A list to investigate, not a refund.`,
      value: leakage.excess_vs_reference_won,
      color: "bg-coral",
    },
  ];
  const max = Math.max(...rows.map((r) => r.value)) || 1;

  return (
    <div className="space-y-4">
      {rows.map((r) => (
        <div key={r.label}>
          <div className="flex items-baseline justify-between gap-4">
            <span className="text-sm font-medium text-ink">{r.label}</span>
            <span className="tabular-nums text-sm font-semibold text-navy">
              {money(r.value)}
            </span>
          </div>
          <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-mist">
            <div
              className={`h-full rounded-full ${r.color}`}
              style={{ width: `${Math.max(2, (r.value / max) * 100)}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate">{r.help}</p>
        </div>
      ))}
    </div>
  );
}
