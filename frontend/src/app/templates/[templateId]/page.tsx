"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, GitBranch, Rocket } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  useLaunchTemplate,
  useTemplate,
  useTemplatePreview,
  useTemplateRuns,
} from "@/lib/hooks/use-templates";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ApiRunCombo, ApiTemplateRunItem, ParamSpec } from "@/lib/types/api";
import type { RunStatus } from "@/lib/types/view";

// ─── Shared helpers ───────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: ParamSpec["role"] }) {
  const cls = {
    fixed: "border-zinc-700 bg-zinc-800 text-zinc-200",
    vary: "border-blue-500/30 bg-blue-500/10 text-blue-200",
    derive: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  } as const;
  return (
    <span
      className={`h-fit rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide ${cls[role]}`}
    >
      {role}
    </span>
  );
}

function describeParam(spec: ParamSpec): string {
  if (spec.role === "fixed") return `= ${spec.value}`;
  if (spec.role === "vary") return `∈ [${spec.values.join(", ")}]`;
  return `${spec.expr}  (from ${spec.from})`;
}

function fmt(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "—";
    if (Number.isInteger(v)) return String(v);
    if (Math.abs(v) < 0.1 && v !== 0) return v.toExponential(2);
    return v.toFixed(4);
  }
  return String(v);
}

const ACTIVE_STATUSES = new Set(["running", "queued", "created"]);

// ─── Config tab ───────────────────────────────────────────────────────────────

function ConfigTab({ params }: { params: Record<string, ParamSpec> }) {
  const groups: Array<{ role: ParamSpec["role"]; label: string }> = [
    { role: "vary", label: "Vary" },
    { role: "derive", label: "Derive" },
    { role: "fixed", label: "Fixed" },
  ];

  return (
    <div className="space-y-4">
      {groups.map(({ role, label }) => {
        const entries = Object.entries(params).filter(([, s]) => s.role === role);
        if (entries.length === 0) return null;
        return (
          <section key={role} className="rounded-2xl border border-zinc-800 bg-zinc-900/70">
            <div className="border-b border-zinc-800 px-4 py-2.5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                {label}
              </h3>
            </div>
            <ul className="divide-y divide-zinc-800">
              {entries.map(([key, spec]) => (
                <li key={key} className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <code className="block truncate font-mono text-sm text-zinc-100">{key}</code>
                    <span className="mt-0.5 block truncate text-xs text-zinc-400">
                      {describeParam(spec)}
                    </span>
                  </div>
                  <RoleBadge role={spec.role} />
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

// ─── Runs tab ─────────────────────────────────────────────────────────────────

function RunRow({ run }: { run: ApiTemplateRunItem }) {
  return (
    <Link
      href={`/runs/${run.run_id}`}
      className="flex items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/70 px-4 py-3 hover:border-zinc-700 hover:bg-zinc-900"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-zinc-100">{run.name}</p>
        <p className="mt-0.5 text-xs text-zinc-500">
          combo #{run.combo_index} · {relativeTime(run.created_at)}
        </p>
      </div>
      {run.metrics?.training_loss != null && (
        <span className="shrink-0 font-mono text-xs text-zinc-400">
          loss {fmt(run.metrics.training_loss)}
        </span>
      )}
      <StatusBadge status={run.status as RunStatus} />
    </Link>
  );
}

function RunsTab({ templateId }: { templateId: string }) {
  const { data, isLoading, isError } = useTemplateRuns(templateId);

  if (isLoading) return <LoadingState />;
  if (isError || !data)
    return (
      <EmptyState title="Could not load runs" description="Check the backend connection." />
    );
  if (data.runs.length === 0)
    return (
      <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 p-8 text-center text-sm text-zinc-500">
        No runs launched from this template yet.
      </div>
    );

  return (
    <ul className="space-y-2">
      {data.runs.map((run) => (
        <li key={run.run_id}>
          <RunRow run={run} />
        </li>
      ))}
    </ul>
  );
}

// ─── Matrix tab ───────────────────────────────────────────────────────────────

function MatrixTab({ templateId }: { templateId: string }) {
  const { data, isLoading, isError } = useTemplatePreview(templateId);

  if (isLoading) return <LoadingState />;
  if (isError || !data)
    return (
      <EmptyState title="Could not load matrix" description="Check the backend connection." />
    );
  if (data.combos.length === 0)
    return (
      <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 p-8 text-center text-sm text-zinc-500">
        No combos to display.
      </div>
    );

  const varyKeys = (() => {
    const first = data.combos[0].params;
    return Object.keys(first).filter((k) =>
      data.combos.some((c) => c.params[k] !== first[k]),
    );
  })();

  const colKeys = varyKeys.length > 0 ? varyKeys : Object.keys(data.combos[0].params);

  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-500">{data.total_runs} combinations</p>
      <div className="overflow-x-auto rounded-2xl border border-zinc-800">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/80">
              <th className="px-3 py-2.5 text-left font-medium text-zinc-500">#</th>
              {colKeys.map((k) => (
                <th key={k} className="px-3 py-2.5 text-left font-medium text-zinc-400">
                  {k.split(".").pop()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.combos.map((combo: ApiRunCombo) => (
              <tr
                key={combo.combo_index}
                className="border-b border-zinc-800/60 last:border-0 hover:bg-zinc-900/40"
              >
                <td className="px-3 py-2 font-mono text-zinc-500">{combo.combo_index}</td>
                {colKeys.map((k) => (
                  <td key={k} className="px-3 py-2 font-mono text-zinc-200">
                    {fmt(combo.params[k])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

type Tab = "config" | "runs" | "matrix";

const TABS: { id: Tab; label: string }[] = [
  { id: "config", label: "Config" },
  { id: "runs", label: "Runs" },
  { id: "matrix", label: "Matrix" },
];

export default function TemplateDetailPage() {
  const { templateId } = useParams<{ templateId: string }>();
  const { data: tpl, isLoading, isError } = useTemplate(templateId);
  const { data: templateRuns } = useTemplateRuns(templateId);
  const { mutate: launch, isPending: launching } = useLaunchTemplate();
  const [activeTab, setActiveTab] = useState<Tab>("config");
  const [launchError, setLaunchError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <AppShell>
        <LoadingState />
      </AppShell>
    );
  }

  if (isError || !tpl) {
    return (
      <AppShell>
        <EmptyState
          title="Template not found"
          description="This template doesn't exist or could not be loaded."
        />
      </AppShell>
    );
  }

  const combos = (() => {
    let n = 1;
    for (const spec of Object.values(tpl.params)) {
      if (spec.role === "vary") n *= Math.max(1, spec.values.length);
    }
    return n;
  })();

  const hasActiveRuns = templateRuns?.runs.some((r) => ACTIVE_STATUSES.has(r.status)) ?? false;
  const launchDisabled = hasActiveRuns || launching;

  function handleLaunch() {
    setLaunchError(null);
    launch(
      { templateId },
      {
        onError: (err) =>
          setLaunchError(err instanceof Error ? err.message : "Launch failed."),
      },
    );
  }

  return (
    <AppShell>
      <div className="space-y-5 pb-28">
        {/* Header */}
        <div>
          <Link
            href="/templates"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Templates
          </Link>
          <h1 className="mt-3 text-2xl font-bold">{tpl.name}</h1>
          {tpl.description ? (
            <p className="mt-1 text-sm text-zinc-400">{tpl.description}</p>
          ) : null}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-3">
            <p className="text-xs text-zinc-500">Params</p>
            <p className="mt-1 text-lg font-semibold text-zinc-100">
              {Object.keys(tpl.params).length}
            </p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-3">
            <div className="flex items-center gap-1 text-xs text-zinc-500">
              <GitBranch className="h-3.5 w-3.5" /> Combos
            </div>
            <p className="mt-1 text-lg font-semibold text-zinc-100">{combos}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-3">
            <p className="text-xs text-zinc-500">Runs</p>
            <p className="mt-1 text-lg font-semibold text-zinc-100">{tpl.run_count}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="-mx-4 flex border-b border-zinc-800 px-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-4 py-2.5 text-sm font-medium transition",
                activeTab === tab.id
                  ? "border-b-2 border-white text-white"
                  : "text-zinc-500 hover:text-zinc-300",
              )}
            >
              {tab.label}
              {tab.id === "runs" && tpl.run_count > 0 && (
                <span className="ml-1.5 rounded-full bg-zinc-800 px-1.5 py-0.5 text-[11px] text-zinc-400">
                  {tpl.run_count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "config" && <ConfigTab params={tpl.params} />}
        {activeTab === "runs" && <RunsTab templateId={templateId} />}
        {activeTab === "matrix" && <MatrixTab templateId={templateId} />}

        {/* Launch error */}
        {launchError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
            {launchError}
          </div>
        )}
      </div>

      {/* Sticky footer */}
      <div className="fixed inset-x-0 bottom-16 z-10 border-t border-zinc-800 bg-zinc-950/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
          <span className="text-xs text-zinc-500">
            {relativeTime(tpl.created_at)}
            {hasActiveRuns && (
              <span className="ml-2 text-amber-400">· runs active</span>
            )}
          </span>
          <button
            type="button"
            onClick={handleLaunch}
            disabled={launchDisabled}
            className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2.5 text-sm font-medium text-black transition hover:bg-zinc-200 disabled:opacity-40"
          >
            <Rocket className="h-4 w-4" />
            {launching ? "Launching…" : "Launch all runs"}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
