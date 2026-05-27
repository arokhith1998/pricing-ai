"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SegmentRow } from "@/lib/api";
import { money, pct } from "@/lib/format";

const NAVY = "#0c2d48";
const TEAL = "#17b8a6";
const MIST = "#e6edf3";
const SLATE = "#5b6b7b";

function SegTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const r: SegmentRow = payload[0].payload;
  return (
    <div className="rounded-lg border border-mist bg-white px-3 py-2 text-sm shadow-md">
      <div className="font-semibold text-navy">{r.segment}</div>
      <div className="text-slate">Price realization {pct(r.price_realization)}</div>
      <div className="text-slate">Average discount {pct(r.avg_discount)}</div>
      <div className="text-slate">
        {r.deals.toLocaleString()} deals, booked {money(r.booked_acv)}
      </div>
    </div>
  );
}

export default function SegmentChart({ rows }: { rows: SegmentRow[] }) {
  // Worst realization first: that is where the money leaks.
  const data = [...rows].sort((a, b) => a.price_realization - b.price_realization);
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={MIST} vertical={false} />
          <XAxis
            dataKey="segment"
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: MIST }}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v) => pct(v, 0)}
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip content={<SegTooltip />} cursor={{ fill: MIST, fillOpacity: 0.4 }} />
          <Bar
            dataKey="price_realization"
            radius={[6, 6, 0, 0]}
            maxBarSize={90}
            isAnimationActive={false}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={i === 0 ? TEAL : NAVY} />
            ))}
            <LabelList
              dataKey="price_realization"
              position="top"
              formatter={(v) => pct(Number(v), 0)}
              fill={SLATE}
              fontSize={12}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
