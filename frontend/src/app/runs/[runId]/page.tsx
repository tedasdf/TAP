"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw, Square } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { DetailTabs, RunDetailTab } from "@/components/run-detail/detail-tabs";
import { OverviewTab } from "@/components/run-detail/overview-tab";
import { MetricsTab } from "@/components/run-detail/metrics-tab";
import { JobTab } from "@/components/run-detail/job-tab";
import { ConfigTab } from "@/components/run-detail/config-tab";
import { RunEventsTimeline } from "@/components/run-detail/RunEventsTimeline";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useCancelRun, useRefreshRun, useRun, useRunEvents, useRunMetricHistory, useRunMetrics, useSyncWandb, useRunMetricSyncStatus } from "@/lib/hooks/use-runs";
import { useJob } from "@/lib/hooks/use-jobs";
import { ApiMetricPoint, ApiRun, ApiRunMetrics } from "@/lib/types/api";
import { RunLogsTab } from "@/components/run-detail/RunLogsTab";
import { RunCardView } from "@/lib/types/view";

function buildOverviewRun(run: ApiRun, metrics?: ApiRunMetrics): RunCardView & {
  wandbRunId?: string | null;
  gitCommit?: string | null;
  createdAt?: string;
  latestMetricTimestamp?: string;
  learningRate?: number;
  configOverrides?: string;
} {
  return {
    id: run.run_id,
    name: run.name,
    status: run.status,
    configPath: run.config_path,
    currentStep: metrics?.current_step ?? run.current_step ?? undefined,
    currentEpoch: metrics?.current_epoch ?? run.current_epoch ?? undefined,
    trainingLoss: metrics?.training_loss ?? run.training_loss ?? undefined,
    validationLoss: metrics?.validation_loss ?? run.validation_loss ?? undefined,
    learningRate: metrics?.learning_rate ?? run.learning_rate ?? undefined,
    runtime:
      metrics?.runtime == null && run.runtime == null
        ? undefined
        : String(metrics?.runtime ?? run.runtime),
    slurmJobId: run.slurm_job_id ?? undefined,
    wandbRunId: run.wandb_run_id ?? undefined,
    gitCommit: run.git_commit ?? undefined,
    createdAt: run.created_at,
    latestMetricTimestamp:
      metrics?.latest_metric_timestamp ?? run.latest_metric_timestamp ?? undefined,
    configOverrides:
      run.config_overrides == null
        ? undefined
        : typeof run.config_overrides === "string"
          ? run.config_overrides
          : JSON.stringify(run.config_overrides, null, 2),
    errorMessage: run.error_message ?? undefined,
  };
}

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;

  const [activeTab, setActiveTab] = useState<RunDetailTab>("overview");

  const runQuery = useRun(runId);
  const metricsQuery = useRunMetrics(runId);
  const metricHistoryQuery = useRunMetricHistory(runId);
  const eventsQuery = useRunEvents(runId);
  const events = eventsQuery.data ?? [];

  const slurmJobId = runQuery.data?.slurm_job_id;
  const jobQuery = useJob(slurmJobId);

  const cancelRunMutation = useCancelRun();
  const refreshRunMutation = useRefreshRun();
  const syncWandbMutation = useSyncWandb();

  const metricSyncStatusQuery = useRunMetricSyncStatus(runId);

  const isLoading =
    runQuery.isLoading ||
    (activeTab === "overview" && metricsQuery.isLoading) ||
    (activeTab === "metrics" && metricHistoryQuery.isLoading) ||
    (activeTab === "job" && !!slurmJobId && jobQuery.isLoading);

  const hasError = runQuery.isError;

  const overviewRun = useMemo(() => {
    if (!runQuery.data) return null;
    return buildOverviewRun(runQuery.data, metricsQuery.data);
  }, [runQuery.data, metricsQuery.data]);

  const metricsSeries = useMemo(() => {
    return (metricHistoryQuery.data ?? []).map((point, index) => ({
      step: point.step ?? index,
      trainingLoss: point.training_loss ?? point.train_loss ?? undefined,
      validationLoss: point.validation_loss ?? point.val_loss ?? undefined,
      learningRate: point.learning_rate ?? undefined,
    }));
  }, [metricHistoryQuery.data]);


  async function handleCancel() {
    if (!runId) return;
    try {
      await cancelRunMutation.mutateAsync(runId);
      await Promise.all([
        runQuery.refetch(),
        eventsQuery.refetch(),
        slurmJobId ? jobQuery.refetch() : Promise.resolve(),
      ]);
    } catch {}
  }

  async function handleRefresh() {
    if (!runId) return;
    try {
      await refreshRunMutation.mutateAsync(runId);
      await Promise.all([
      runQuery.refetch(),
      metricsQuery.refetch(),
      metricHistoryQuery.refetch(),
      eventsQuery.refetch(),
      slurmJobId ? jobQuery.refetch() : Promise.resolve(),
    ]);
    } catch {}
  }

  async function handleSync() {
    if (!runId) return;
    try {
      await syncWandbMutation.mutateAsync(runId);
    } catch {}
  }

  return (
    <AppShell>
      <div className="space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <Link
              href="/runs"
              className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Runs
            </Link>

            <p className="mt-3 text-sm text-zinc-500">Run Detail</p>
            <h1 className="mt-1 text-2xl font-bold">
              {runQuery.data?.name ?? "Loading run..."}
            </h1>
            <p className="mt-2 text-sm text-zinc-400">
              {runQuery.data?.config_path ?? ""}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshRunMutation.isPending}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-zinc-800 bg-zinc-900/70 px-4 py-3 text-sm text-zinc-200 disabled:opacity-60"
          >
            <RefreshCw className="h-4 w-4" />
            {refreshRunMutation.isPending ? "Refreshing..." : "Refresh"}
          </button>

          <button
            type="button"
            onClick={handleSync}
            disabled={syncWandbMutation.isPending}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-zinc-800 bg-zinc-900/70 px-4 py-3 text-sm text-zinc-200 disabled:opacity-60"
          >
            <RefreshCw className="h-4 w-4" />
            Sync
          </button>

          <button
            type="button"
            onClick={handleCancel}
            disabled={cancelRunMutation.isPending}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200 disabled:opacity-60"
          >
            <Square className="h-4 w-4" />
            Cancel
          </button>
        </div>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
          <div className="mb-3">
            <h2 className="text-lg font-semibold">Timeline</h2>
            <p className="text-sm text-zinc-400">
              Run lifecycle events recorded by TAP.
            </p>
          </div>

          <RunEventsTimeline events={events} />
        </section>

        <DetailTabs activeTab={activeTab} onChange={setActiveTab} />

        {isLoading ? (
          <LoadingState />
        ) : hasError || !runQuery.data ? (
          <EmptyState
            title="Could not load run"
            description="Check the backend connection and try again."
          />
        ) : (
          <>
            {activeTab === "overview" && overviewRun && <OverviewTab run={overviewRun} />}

            {activeTab === "metrics" && (
              <div className="space-y-4">
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 text-sm">
                  <p className="font-semibold text-white">Metric Sync Status</p>

                  <div className="mt-3 space-y-1 text-zinc-300">
                    <p>Status: {metricSyncStatusQuery.data?.status ?? "unknown"}</p>
                    <p>Source: {metricSyncStatusQuery.data?.source ?? "—"}</p>
                    <p>Last synced: {metricSyncStatusQuery.data?.last_finished_at ?? "—"}</p>
                    <p>Points synced: {metricSyncStatusQuery.data?.points_synced ?? 0}</p>

                    {metricSyncStatusQuery.data?.error_message ? (
                      <p className="text-red-300">
                        Error: {metricSyncStatusQuery.data.error_message}
                      </p>
                    ) : null}
                  </div>
                </div>

                {metricsSeries.length > 0 ? (
                  <MetricsTab data={metricsSeries} />
                ) : (
                  <EmptyState
                    title="No metric history yet"
                    description="This run has no real metric history yet. Sync W&B or upsert metric points before showing charts."
                  />
                )}
              </div>
            )}

            {activeTab === "logs" && (
              <RunLogsTab runId={runQuery.data.run_id} />
            )}

            {activeTab === "job" &&
              (slurmJobId ? (
                jobQuery.data ? (
                  <JobTab
                    job={{
                      jobId: jobQuery.data.job_id,
                      queueState: jobQuery.data.queue_state ?? "—",
                      executionState: jobQuery.data.execution_state ?? "—",
                      nodeInfo: jobQuery.data.node_info ?? "—",
                      startTime: jobQuery.data.start_time ?? "—",
                      endTime: jobQuery.data.end_time ?? "—",
                      exitStatus: jobQuery.data.exit_status ?? "—",
                      logPath: jobQuery.data.log_path ?? "—",
                      errorLogPath: jobQuery.data.error_log_path ?? "—",
                    }}
                  />
                ) : (
                  <EmptyState
                    title="No job details"
                    description="Job details are not available yet."
                  />
                )
              ) : (
                <EmptyState
                  title="No Slurm job"
                  description="This run does not have a Slurm job ID yet."
                />
              ))}

            {activeTab === "config" && (
              <ConfigTab
                configPath={runQuery.data.config_path}
                configOverrides={runQuery.data.config_overrides ?? undefined}
                gitCommit={runQuery.data.git_commit ?? undefined}
                wandbRunId={runQuery.data.wandb_run_id ?? undefined}
                configSnapshot={runQuery.data.config_snapshot ?? undefined}
              />
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}