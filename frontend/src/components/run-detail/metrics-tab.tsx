"use client";

import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { ApiMetricPoint } from "@/lib/types/api";

const LINE_COLORS = [
  "#fafafa", "#38bdf8", "#4ade80", "#f97316",
  "#e879f9", "#fb7185", "#facc15", "#a78bfa",
];

const DEFAULT_KEYS = [
  "train/loss", "training_loss",
  "eval/val_loss", "validation_loss",
];

type MetricsTabProps = {
  data: ApiMetricPoint[];
};

function MetricChart({
  metricKey,
  data,
  color,
}: {
  metricKey: string;
  data: ApiMetricPoint[];
  color: string;
}) {
  const chartData = data.map((p) => ({
    step: p.step,
    value: p.metrics[metricKey] ?? null,
  })).filter((p) => p.value !== null);

  if (chartData.length === 0) return null;

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <h3 className="text-sm font-semibold text-white">{metricKey}</h3>
      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
            <XAxis dataKey="step" stroke="#71717a" fontSize={11} />
            <YAxis stroke="#71717a" fontSize={11} width={60} />
            <Tooltip
              contentStyle={{
                background: "#09090b",
                border: "1px solid #27272a",
                borderRadius: 12,
                color: "#fff",
                fontSize: 12,
              }}
              formatter={(v) => [typeof v === "number" ? v.toPrecision(5) : v, metricKey]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              dot={false}
              strokeWidth={2}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function MetricsTab({ data }: MetricsTabProps) {
  const allKeys = useMemo(() => {
    const keys = new Set<string>();
    data.forEach((p) => Object.keys(p.metrics).forEach((k) => keys.add(k)));
    return Array.from(keys).sort();
  }, [data]);

  const [selected, setSelected] = useState<Set<string>>(() => {
    const defaults = DEFAULT_KEYS.filter((k) => allKeys.includes(k));
    return new Set(defaults.length ? defaults : allKeys.slice(0, 2));
  });

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  if (data.length === 0) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-8 text-center text-sm text-zinc-500">
        No metric history yet. Points appear after the first log call.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* key selector */}
      <div className="flex flex-wrap gap-2">
        {allKeys.map((key, i) => (
          <button
            key={key}
            type="button"
            onClick={() => toggle(key)}
            className={[
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              selected.has(key)
                ? "border-transparent text-zinc-900"
                : "border-zinc-700 bg-transparent text-zinc-400 hover:border-zinc-500",
            ].join(" ")}
            style={selected.has(key) ? { backgroundColor: LINE_COLORS[i % LINE_COLORS.length] } : undefined}
          >
            {key}
          </button>
        ))}
      </div>

      {/* charts */}
      {Array.from(selected).map((key) => {
        const colorIdx = allKeys.indexOf(key) % LINE_COLORS.length;
        return (
          <MetricChart
            key={key}
            metricKey={key}
            data={data}
            color={LINE_COLORS[colorIdx]}
          />
        );
      })}
    </div>
  );
}
