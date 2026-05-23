"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronRight, LayoutTemplate, Trash2, X } from "lucide-react";
import { RunCardView } from "@/lib/types/view";
import { StatusBadge } from "@/components/shared/status-badge";

type RunCardProps = {
  run: RunCardView;
  onDelete?: (runId: string) => void;
  isDeleting?: boolean;
};

export function RunCard({ run, onDelete, isDeleting }: RunCardProps) {
  const [confirming, setConfirming] = useState(false);

  function handleDeleteClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setConfirming(true);
  }

  function handleConfirm(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    onDelete?.(run.id);
    setConfirming(false);
  }

  function handleCancel(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setConfirming(false);
  }

  return (
    <div className="relative">
      <Link
        href={`/runs/${run.id}`}
        className="block rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 transition hover:border-zinc-700"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-white">{run.name}</h3>
            <p className="mt-1 truncate text-xs text-zinc-400">{run.configPath}</p>
            {run.templateId ? (
              <Link
                href={`/templates/${run.templateId}`}
                onClick={(e) => e.stopPropagation()}
                className="mt-1.5 inline-flex items-center gap-1 rounded-full border border-zinc-700/60 bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-200"
              >
                <LayoutTemplate className="h-3 w-3" />
                From template
              </Link>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={run.status} />
            {onDelete && (
              <button
                type="button"
                onClick={handleDeleteClick}
                aria-label="Delete run"
                className="rounded-lg p-1 text-zinc-600 transition hover:bg-red-500/10 hover:text-red-400"
                disabled={isDeleting}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-zinc-300">
          <div>
            <p className="text-zinc-500">Step</p>
            <p>{run.currentStep ?? "—"}</p>
          </div>
          <div>
            <p className="text-zinc-500">Epoch</p>
            <p>{run.currentEpoch ?? "—"}</p>
          </div>
          <div>
            <p className="text-zinc-500">Train</p>
            <p>{run.trainingLoss ?? "—"}</p>
          </div>
          <div>
            <p className="text-zinc-500">Val</p>
            <p>{run.validationLoss ?? "—"}</p>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-zinc-400">Runtime: {run.runtime ?? "—"}</p>
          <span className="inline-flex items-center gap-1 text-xs text-zinc-400">
            Open <ChevronRight className="h-3.5 w-3.5" />
          </span>
        </div>

        {run.errorMessage ? (
          <div className="mt-3 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-200">
            {run.errorMessage}
          </div>
        ) : null}
      </Link>

      {confirming && (
        <div className="absolute inset-0 z-10 flex flex-col justify-between rounded-2xl border border-red-500/30 bg-zinc-900 p-4">
          <div>
            <p className="text-sm font-semibold text-zinc-100">Delete this run?</p>
            <p className="mt-1 text-xs text-zinc-400">
              <span className="text-zinc-200">{run.name}</span> will be permanently removed.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleCancel}
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300"
            >
              <X className="h-3.5 w-3.5" /> Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isDeleting}
              className="inline-flex items-center gap-1 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-200 disabled:opacity-60"
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
