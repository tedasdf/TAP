"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronRight, GitBranch, LayoutTemplate, Plus, Rocket } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { MatrixPreviewSheet } from "@/components/MatrixPreviewSheet";
import { useTemplates, useLaunchTemplate } from "@/lib/hooks/use-templates";
import { relativeTime } from "@/lib/format";
import type { ApiTemplate, ParamSpec } from "@/lib/types/api";

function varyParamSummary(params: Record<string, ParamSpec>): string {
  const keys = Object.keys(params).filter((k) => params[k].role === "vary");
  return keys.length > 0 ? keys.join(" × ") : "no vary params";
}

function combinationCount(params: Record<string, ParamSpec>): number {
  let n = 1;
  for (const spec of Object.values(params)) {
    if (spec.role === "vary") n *= Math.max(1, spec.values.length);
  }
  return n;
}

function TemplateCard({
  template,
  onPreview,
  onLaunch,
  launching,
}: {
  template: ApiTemplate;
  onPreview: (id: string) => void;
  onLaunch: (id: string) => void;
  launching: boolean;
}) {
  const combos = combinationCount(template.params);
  const summary = varyParamSummary(template.params);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <Link
        href={`/templates/${template.template_id}`}
        className="group flex items-start justify-between gap-3"
      >
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-zinc-100 group-hover:text-white">
            {template.name}
          </h3>
          {template.description ? (
            <p className="mt-1 line-clamp-2 text-sm text-zinc-400">{template.description}</p>
          ) : null}
        </div>
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-zinc-600 transition group-hover:text-zinc-300" />
      </Link>

      <p className="mt-2 truncate font-mono text-xs text-zinc-400" title={summary}>
        {summary}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="inline-flex items-center gap-1 rounded-full border border-zinc-700/70 bg-zinc-800/60 px-2 py-0.5 text-zinc-200">
          <GitBranch className="h-3.5 w-3.5" />
          {combos} combo{combos === 1 ? "" : "s"}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-zinc-400">
          {template.run_count} run{template.run_count === 1 ? "" : "s"} launched
        </span>
        <span className="ml-auto text-zinc-500">{relativeTime(template.created_at)}</span>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => onPreview(template.template_id)}
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 py-1.5 text-xs font-medium text-zinc-200 transition hover:bg-zinc-700"
        >
          Preview
        </button>
        <button
          type="button"
          onClick={() => onLaunch(template.template_id)}
          disabled={launching}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-white py-1.5 text-xs font-medium text-black transition hover:bg-zinc-200 disabled:opacity-50"
        >
          <Rocket className="h-3.5 w-3.5" />
          {launching ? "Launching…" : "Launch"}
        </button>
      </div>
    </div>
  );
}

export default function TemplatesPage() {
  const { data, isLoading, isError } = useTemplates();
  const { mutate: launch, isPending } = useLaunchTemplate();
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);

  function handleLaunchClick(id: string) {
    setConfirmId(id);
  }

  function handleConfirm() {
    if (!confirmId) return;
    launch(
      { templateId: confirmId },
      { onSettled: () => setConfirmId(null) },
    );
  }

  return (
    <AppShell>
      <MatrixPreviewSheet
        templateId={previewId ?? ""}
        open={previewId !== null}
        onClose={() => setPreviewId(null)}
        onLaunch={() => {
          if (previewId) launch({ templateId: previewId });
          setPreviewId(null);
        }}
      />

      <div className="space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-zinc-500">TAP</p>
            <h1 className="mt-1 text-2xl font-bold">Templates</h1>
            <p className="mt-2 text-sm text-zinc-400">
              Parameterized sweeps — one template, many runs.
            </p>
          </div>
          <Link
            href="/templates/new"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-white px-3 py-2 text-sm font-medium text-black transition hover:bg-zinc-200"
          >
            <Plus className="h-4 w-4" /> New
          </Link>
        </div>

        {/* Launch confirmation dialog */}
        {confirmId ? (
          <div className="rounded-2xl border border-zinc-700 bg-zinc-900 p-4">
            <p className="text-sm text-zinc-200">
              Launch all runs for{" "}
              <span className="font-semibold">
                {data?.find((t) => t.template_id === confirmId)?.name ?? confirmId}
              </span>
              ? This will submit jobs to Slurm.
            </p>
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => setConfirmId(null)}
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 py-1.5 text-sm text-zinc-300 transition hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={isPending}
                className="flex-1 rounded-lg bg-white py-1.5 text-sm font-medium text-black transition hover:bg-zinc-200 disabled:opacity-50"
              >
                {isPending ? "Launching…" : "Confirm launch"}
              </button>
            </div>
          </div>
        ) : null}

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <EmptyState
            title="Could not load templates"
            description="Check the backend connection and try again."
          />
        ) : !data || data.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 p-10 text-center">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-zinc-800/80">
              <LayoutTemplate className="h-6 w-6 text-zinc-300" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-zinc-100">No templates yet</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Templates let you launch a sweep of runs from one parameter spec.
            </p>
            <Link
              href="/templates/new"
              className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-zinc-200"
            >
              <Plus className="h-4 w-4" /> Create your first template
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {data.map((t) => (
              <li key={t.template_id}>
                <TemplateCard
                  template={t}
                  onPreview={setPreviewId}
                  onLaunch={handleLaunchClick}
                  launching={isPending && confirmId === t.template_id}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
