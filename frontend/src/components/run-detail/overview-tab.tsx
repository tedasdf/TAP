import Link from "next/link";
import { RunCardView } from "@/lib/types/view";
import { StatusBadge } from "@/components/shared/status-badge";

type OverviewTabProps = {
  run: RunCardView & {
    wandbRunId?: string | null;
    gitCommit?: string | null;
    createdAt?: string;
    latestMetricTimestamp?: string;
    learningRate?: number;
    configOverrides?: Record<string, unknown> | string | null;
    templateId?: string | null;
  };
};

export function OverviewTab({ run }: OverviewTabProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-white">{run.name}</h2>
            <p className="mt-1 text-sm text-zinc-400">{run.configPath}</p>
          </div>
          <StatusBadge status={run.status} />
        </div>

        {run.errorMessage ? (
          <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
            {run.errorMessage}
          </div>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs text-zinc-500">Step</p>
          <p className="mt-2 text-xl font-semibold text-white">{run.currentStep ?? "—"}</p>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs text-zinc-500">Epoch</p>
          <p className="mt-2 text-xl font-semibold text-white">{run.currentEpoch ?? "—"}</p>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs text-zinc-500">Training Loss</p>
          <p className="mt-2 text-xl font-semibold text-white">{run.trainingLoss ?? "—"}</p>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs text-zinc-500">Validation Loss</p>
          <p className="mt-2 text-xl font-semibold text-white">{run.validationLoss ?? "—"}</p>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs text-zinc-500">Runtime</p>
          <p className="mt-2 text-xl font-semibold text-white">{run.runtime ?? "—"}</p>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs text-zinc-500">Learning Rate</p>
          <p className="mt-2 text-xl font-semibold text-white">{run.learningRate ?? "—"}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Run Metadata</h3>

        <div className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Run ID</span>
            <span className="text-right text-zinc-200">{run.id}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Slurm Job ID</span>
            <span className="text-right text-zinc-200">{run.slurmJobId ?? "—"}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">W&B Run ID</span>
            <span className="text-right text-zinc-200">{run.wandbRunId ?? "—"}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Created</span>
            <span className="text-right text-zinc-200">{run.createdAt ?? "—"}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Latest Metric Update</span>
            <span className="text-right text-zinc-200">{run.latestMetricTimestamp ?? "—"}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Git Commit</span>
            <span className="text-right text-zinc-200">{run.gitCommit ?? "—"}</span>
          </div>

          {run.templateId ? (
            <div className="flex justify-between gap-4">
              <span className="text-zinc-500">From template</span>
              <Link
                href={`/templates/${run.templateId}`}
                className="text-right text-blue-400 hover:underline"
              >
                View template
              </Link>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}