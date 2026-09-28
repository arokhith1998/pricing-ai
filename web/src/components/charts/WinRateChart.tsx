"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ReferenceDiscount, WinRateBand } from "@/lib/api";
import { pct } from "@/lib/format";

const NAVY = "#e9f0f8"; // win-rate line, light on dark
const TEAL = "#2dd4bf";
const CORAL = "#ff6b54";
const MIST = "#1f2c43"; // grid
const SLATE = "#8ea3bd"; // axis text

type Row = {
  band: string;
  winRate: number;
  ci: [number, number];
  deals: number;
  avgDiscount: number;
};

// Minimal shape we use from Recharts' Tooltip `content` callback; their
// own generics are messy enough that a narrow local type is cleaner.
// Both `payload` and `payload[i].payload` are optional in Recharts' shape.
type TooltipProps<T> = {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: T }>;
};

function PointTooltip({ active, payload }: TooltipProps<Row>) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  if (!r) return null;
  return (
    <div className="rounded-lg border border-mist bg-surface px-3 py-2 text-sm shadow-md">
      <div className="font-semibold text-fg">{r.band} discount</div>
      <div className="text-slate">Win rate {pct(r.winRate)}</div>
      <div className="text-slate">
        {r.deals.toLocaleString()} deals, average discount {pct(r.avgDiscount)}
      </div>
    </div>
  );
}

export default function WinRateChart({
  bands,
  reference,
}: {
  bands: WinRateBand[];
  reference: ReferenceDiscount;
}) {
  const ci = reference.band_win_rate_ci;
  const data: Row[] = bands.map((b) => {
    const c = ci[b.discount_band];
    return {
      band: b.discount_band,
      winRate: b.win_rate,
      ci: c ? [c[1], c[2]] : [b.win_rate, b.win_rate],
      deals: b.deals,
      avgDiscount: b.avg_discount,
    };
  });

  return (
    // 2026-09-27 review: /diagnostic overflowed at a 390px viewport.
    // Recharts' ResponsiveContainer used to be given `initialDimension`
    // (a guessed pixel width) to render before its ResizeObserver had
    // measured the real container even once; on a narrow viewport that
    // guess was wider than the viewport, and its measuring wrapper is
    // deliberately width:0/overflow-visible (a documented recharts trick so
    // the chart can shrink), so nothing clipped the oversized first render
    // and it widened the whole document. Without `initialDimension`,
    // recharts renders nothing until it has measured a real, positive size
    // (its mount effect measures synchronously, before paint, so this is not
    // visually a flash of empty space in practice) instead of guessing a
    // fixed width that can be wrong. `overflow-hidden` is defense in depth
    // for the rare environment where ResizeObserver itself is unavailable.
    <div className="h-72 min-w-0 w-full overflow-hidden">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={1}>
        <ComposedChart data={data} margin={{ top: 28, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={MIST} vertical={false} />
          <XAxis
            dataKey="band"
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: MIST }}
          />
          <YAxis
            domain={[0, 0.8]}
            tickFormatter={(v) => pct(v, 0)}
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip content={<PointTooltip />} />
          <Area
            type="monotone"
            dataKey="ci"
            stroke="none"
            fill={TEAL}
            fillOpacity={0.14}
            isAnimationActive={false}
          />
          <ReferenceLine
            x={reference.reference_band}
            stroke={CORAL}
            strokeDasharray="4 4"
            label={{
              value: "win point",
              position: "top",
              fill: CORAL,
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="winRate"
            stroke={NAVY}
            strokeWidth={2.5}
            dot={{ r: 3, fill: NAVY }}
            activeDot={{ r: 5 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
