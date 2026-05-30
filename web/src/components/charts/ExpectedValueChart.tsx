"use client";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CurvePoint } from "@/lib/api";
import { money, moneyShort, pct, pct0 } from "@/lib/format";

const NAVY = "#e9f0f8"; // expected-value line, light on dark
const TEAL = "#2dd4bf";
const CORAL = "#ff6b54";
const MIST = "#1f2c43"; // grid
const SLATE = "#8ea3bd"; // axis text

// Minimal shape we use from Recharts' Tooltip `content` callback.
// Both `payload` and `payload[i].payload` are optional in Recharts' shape.
type TooltipProps<T> = {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: T }>;
};

function CurveTooltip({ active, payload }: TooltipProps<CurvePoint>) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (!p) return null;
  return (
    <div className="rounded-lg border border-mist bg-surface px-3 py-2 text-sm shadow-md">
      <div className="font-semibold text-fg">{pct0(p.discount)} discount</div>
      <div className="text-slate">Expected value {money(p.expected_acv)}</div>
      <div className="text-slate">Win probability {pct(p.win_prob)}</div>
    </div>
  );
}

export default function ExpectedValueChart({
  curve,
  current,
  recommended,
}: {
  curve: CurvePoint[];
  current: number;
  recommended: number;
}) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={curve} margin={{ top: 28, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={MIST} vertical={false} />
          <XAxis
            dataKey="discount"
            type="number"
            domain={[0, 0.4]}
            tickFormatter={(v) => pct0(v)}
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: MIST }}
          />
          <YAxis
            yAxisId="acv"
            tickFormatter={(v) => moneyShort(v)}
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={52}
          />
          <YAxis
            yAxisId="p"
            orientation="right"
            domain={[0, 1]}
            tickFormatter={(v) => pct0(v)}
            tick={{ fill: SLATE, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip content={<CurveTooltip />} />
          <ReferenceLine
            yAxisId="acv"
            x={current}
            stroke={SLATE}
            strokeDasharray="4 4"
            label={{ value: "current", position: "top", fill: SLATE, fontSize: 12 }}
          />
          <ReferenceLine
            yAxisId="acv"
            x={recommended}
            stroke={TEAL}
            strokeWidth={1.5}
            label={{ value: "best", position: "top", fill: TEAL, fontSize: 12 }}
          />
          <Line
            yAxisId="acv"
            type="monotone"
            dataKey="expected_acv"
            name="Expected value"
            stroke={NAVY}
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            yAxisId="p"
            type="monotone"
            dataKey="win_prob"
            name="Win probability"
            stroke={CORAL}
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
