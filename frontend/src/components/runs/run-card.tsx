import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { RunCardView } from "@/lib/types/view";
import { StatusBadge } from "@/components/shared/status-badge";

type RunCardProps = {
  run: RunCardView;
};

export function RunCard({ run }: RunCardProps) {
  return (
    <Link
      href={`/runs/${run.id}`}
      className="block rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 transition hover:border-zinc-700"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-white">{run.name}</h3>
          <p className="mt-1 truncate text-xs text-zinc-400">{run.configPath}</p>
        </div>
        <StatusBadge status={run.status} />
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
  );
}