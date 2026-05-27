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

const NAVY = "#0c2d48";
const TEAL = "#17b8a6";
const CORAL = "#f0654e";
const MIST = "#e6edf3";
const SLATE = "#5b6b7b";

type Row = {
  band: string;
  winRate: number;
  ci: [number, number];
  deals: number;
  avgDiscount: number;
};

function PointTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const r: Row = payload[0].payload;
  return (
    <div className="rounded-lg border border-mist bg-white px-3 py-2 text-sm shadow-md">
      <div className="font-semibold text-navy">{r.band} discount</div>
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
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
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
