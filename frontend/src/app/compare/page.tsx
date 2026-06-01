"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, X, GitCompareArrows, TrendingDown, Trophy, Clock, Hash, Layers } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { StatusBadge } from "@/components/shared/status-badge";
import { LoadingState } from "@/components/shared/loading-state";
import { EmptyState } from "@/components/shared/empty-state";
import { useRuns } from "@/lib/hooks/use-runs";
import { compareRuns } from "@/lib/api/runs";
import { ApiCompareEntry, ApiCompareResponse } from "@/lib/types/api";

// ─── helpers ──────────────────────────────────────────────────────────────────

function fmt(val: number | null | undefined, decimals = 4): string {
  if (val == null) return "—";
  return val.toFixed(decimals);
}

function fmtRuntime(secs: number | null | undefined): string {
  if (secs == null) return "—";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function best(entries: ApiCompareEntry[], key: keyof ApiCompareEntry, mode: "min" | "max"): string | null {
  let bestId: string | null = null;
  let bestVal: number | null = null;
  for (const e of entries) {
    const v = e[key] as number | null;
    if (v == null) continue;
    if (bestVal == null || (mode === "min" ? v < bestVal : v > bestVal)) {
      bestVal = v;
      bestId = e.run_id;
    }
  }
  return bestId;
}

// ─── sub-components ───────────────────────────────────────────────────────────

function MetricCell({
  value,
  formatted,
  isBest,
}: {
  value: number | null;
  formatted: string;
  isBest: boolean;
}) {
  return (
    <td
      className={`px-4 py-3 text-right text-sm tabular-nums transition-colors ${
        value == null
          ? "text-zinc-600"
          : isBest
          ? "text-emerald-300 font-semibold"
          : "text-zinc-200"
      }`}
    >
      {isBest && value != null && (
        <Trophy className="mr-1 inline h-3 w-3 text-emerald-400" />
      )}
      {formatted}
    </td>
  );
}

function DiffTable({ diff }: { diff: Record<string, Record<string, unknown>> }) {
  const keys = Object.keys(diff);
  if (keys.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-zinc-500">
        No config differences found between these runs.
      </p>
    );
  }

  const runIds = Object.keys(diff[keys[0]]);

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500">
              Config key
            </th>
            {runIds.map((id) => (
              <th
                key={id}
                className="px-4 py-3 text-right text-xs font-medium text-zinc-500"
              >
                {id.slice(0, 8)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/60">
          {keys.map((key) => (
            <tr key={key} className="hover:bg-zinc-800/30">
              <td className="px-4 py-3 font-mono text-xs text-zinc-300">{key}</td>
              {runIds.map((id) => {
                const val = diff[key][id];
                return (
                  <td
                    key={id}
                    className="px-4 py-3 text-right font-mono text-xs text-amber-300"
                  >
                    {val == null ? <span className="text-zinc-600">—</span> : String(val)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function ComparePage() {
  const { data: allRuns, isLoading: runsLoading } = useRuns();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"metrics" | "config">("metrics");

  const canCompare = selectedIds.length >= 2;

  const {
    data: compareData,
    isLoading: comparing,
    isError,
    refetch,
  } = useQuery<ApiCompareResponse>({
    queryKey: ["compare", selectedIds],
    queryFn: () => compareRuns(selectedIds),
    enabled: canCompare,
  });

  const bestValLossId = useMemo(
    () => best(compareData?.runs ?? [], "best_validation_loss", "min"),
    [compareData]
  );
  const bestTrainLossId = useMemo(
    () => best(compareData?.runs ?? [], "training_loss", "min"),
    [compareData]
  );
  const fastestId = useMemo(
    () => best(compareData?.runs ?? [], "runtime", "min"),
    [compareData]
  );
  const mostStepsId = useMemo(
    () => best(compareData?.runs ?? [], "current_step", "max"),
    [compareData]
  );

  function toggleRun(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : prev.length < 5
        ? [...prev, id]
        : prev
    );
  }

  return (
    <AppShell>
      <div className="pb-24">
        {/* header */}
        <div className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-950 p-4">
          <div className="flex items-center gap-3">
            <GitCompareArrows className="h-5 w-5 text-zinc-400" />
            <h1 className="text-xl font-semibold text-zinc-100">Compare runs</h1>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            Select 2–5 runs to compare metrics and config differences.
          </p>
        </div>

        {/* run picker */}
        <div className="border-b border-zinc-800 p-4">
          <p className="mb-3 text-xs font-medium text-zinc-400">
            Selected ({selectedIds.length}/5)
          </p>

          {runsLoading ? (
            <LoadingState />
          ) : (
            <div className="space-y-2">
              {(allRuns ?? []).map((run) => {
                const selected = selectedIds.includes(run.run_id);
                return (
                  <button
                    key={run.run_id}
                    onClick={() => toggleRun(run.run_id)}
                    className={`flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left transition-colors ${
                      selected
                        ? "border-blue-500/40 bg-blue-500/10"
                        : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-zinc-100">
                        {run.name}
                      </p>
                      <p className="truncate text-xs text-zinc-500">
                        {run.run_id.slice(0, 12)}…
                      </p>
                    </div>
                    <div className="ml-3 flex shrink-0 items-center gap-2">
                      <StatusBadge status={run.status} />
                      {selected ? (
                        <X className="h-4 w-4 text-blue-400" />
                      ) : (
                        <Plus className="h-4 w-4 text-zinc-500" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* results */}
        {!canCompare ? (
          <div className="p-8 text-center">
            <GitCompareArrows className="mx-auto mb-3 h-10 w-10 text-zinc-700" />
            <p className="text-sm text-zinc-500">Select at least 2 runs to compare</p>
          </div>
        ) : comparing ? (
          <div className="p-8">
            <LoadingState />
          </div>
        ) : isError ? (
          <div className="p-4">
            <EmptyState
              title="Compare failed"
              description="Could not load comparison data. Check the backend."
            />
          </div>
        ) : compareData ? (
          <div className="p-4 space-y-4">
            {/* tab switcher */}
            <div className="flex gap-2">
              {(["metrics", "config"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
                    activeTab === tab
                      ? "bg-blue-600 text-white"
                      : "border border-zinc-800 bg-zinc-900 text-zinc-400"
                  }`}
                >
                  {tab === "metrics" ? "Metrics" : "Config diff"}
                </button>
              ))}
            </div>

            {activeTab === "metrics" && (
              <>
                {/* summary cards */}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    {
                      label: "Best val loss",
                      icon: TrendingDown,
                      runId: bestValLossId,
                      color: "emerald",
                    },
                    {
                      label: "Best train loss",
                      icon: TrendingDown,
                      runId: bestTrainLossId,
                      color: "blue",
                    },
                    {
                      label: "Fastest",
                      icon: Clock,
                      runId: fastestId,
                      color: "amber",
                    },
                    {
                      label: "Most steps",
                      icon: Hash,
                      runId: mostStepsId,
                      color: "purple",
                    },
                  ].map(({ label, icon: Icon, runId, color }) => {
                    const run = compareData.runs.find((r) => r.run_id === runId);
                    return (
                      <div
                        key={label}
                        className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-3"
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <Icon className={`h-3.5 w-3.5 text-${color}-400`} />
                          <p className="text-xs text-zinc-500">{label}</p>
                        </div>
                        <p className="text-sm font-semibold text-zinc-100 truncate">
                          {run ? run.name : "—"}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* metrics table */}
                <div className="overflow-x-auto rounded-xl border border-zinc-800">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800">
                        <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500">
                          Run
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-zinc-500">
                          Status
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-zinc-500">
                          Train loss
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-zinc-500">
                          Val loss
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-zinc-500">
                          Best val
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-zinc-500">
                          Step
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-zinc-500">
                          Runtime
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60">
                      {compareData.runs.map((entry) => (
                        <tr key={entry.run_id} className="hover:bg-zinc-800/30">
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-zinc-100 truncate max-w-[120px]">
                              {entry.name}
                            </p>
                            <p className="text-xs text-zinc-600 font-mono">
                              {entry.run_id.slice(0, 8)}
                            </p>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <StatusBadge status={entry.status} />
                          </td>
                          <MetricCell
                            value={entry.training_loss}
                            formatted={fmt(entry.training_loss)}
                            isBest={entry.run_id === bestTrainLossId}
                          />
                          <MetricCell
                            value={entry.validation_loss}
                            formatted={fmt(entry.validation_loss)}
                            isBest={false}
                          />
                          <MetricCell
                            value={entry.best_validation_loss}
                            formatted={fmt(entry.best_validation_loss)}
                            isBest={entry.run_id === bestValLossId}
                          />
                          <td className="px-4 py-3 text-right text-sm tabular-nums text-zinc-300">
                            {entry.current_step ?? "—"}
                          </td>
                          <MetricCell
                            value={entry.runtime}
                            formatted={fmtRuntime(entry.runtime)}
                            isBest={entry.run_id === fastestId}
                          />
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {activeTab === "config" && (
              <>
                <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
                  <Layers className="h-3.5 w-3.5" />
                  Only showing keys where runs differ
                </div>
                <DiffTable diff={compareData.config_diff} />
              </>
            )}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}