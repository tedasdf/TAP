"use client";

import { AppShell } from "@/components/layout/app-shell";
import { CurrentRuns } from "@/components/home/current-runs";
import { NeedsAttention } from "@/components/home/needs-attention";
import { QuickActions } from "@/components/home/quick-actions";
import { RecentAlerts } from "@/components/home/recent-alerts";
import { StatusStrip } from "@/components/home/status-strip";
import { SummarySection } from "@/components/home/summary-section";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useNotifications } from "@/lib/hooks/use-notifications";
import { useRuns } from "@/lib/hooks/use-runs";
import { useSystemStatus } from "@/lib/hooks/use-system";
import { ApiNotification, ApiRun, ApiSystemStatus } from "@/lib/types/api";
import {
  AlertView,
  AttentionItem,
  RunCardView,
  StatusStripView,
  SummaryCounts,
} from "@/lib/types/view";

function mapSystemStatusToView(status?: ApiSystemStatus): StatusStripView {
  const normalize = (
    value?: string,
  ): "healthy" | "connected" | "degraded" | "disconnected" | "unknown" => {
    if (!value) return "unknown";

    const v = value.toLowerCase();

    if (["healthy", "ok", "up"].includes(v)) return "healthy";
    if (["connected", "reachable", "online"].includes(v)) return "connected";
    if (["degraded", "warning"].includes(v)) return "degraded";
    if (["disconnected", "down", "offline", "unreachable", "error"].includes(v)) {
      return "disconnected";
    }

    return "unknown";
  };

  return {
    backend: normalize(status?.backend),
    m3: normalize(status?.m3),
    slurm: normalize(status?.slurm),
    wandb: normalize(status?.wandb),
  };
}

function mapRunToCardView(run: ApiRun): RunCardView {
  return {
    id: run.run_id,
    name: run.name,
    status: run.status,
    configPath: run.config_path,
    currentStep: run.current_step ?? undefined,
    currentEpoch: run.current_epoch ?? undefined,
    trainingLoss: run.training_loss ?? undefined,
    validationLoss: run.validation_loss ?? undefined,
    runtime: run.runtime ?? undefined,
    errorMessage: run.error_message ?? undefined,
    slurmJobId: run.slurm_job_id ?? undefined,
  };
}

function mapNotificationToAlertView(notification: ApiNotification): AlertView {
  const rawType = notification.event_type.toLowerCase();

  let type: AlertView["type"] = "info";
  if (rawType.includes("fail") || rawType.includes("error")) type = "error";
  else if (rawType.includes("warn")) type = "warning";
  else if (rawType.includes("complete") || rawType.includes("success")) type = "success";

  return {
    id: notification.notification_id,
    type,
    title: notification.event_type.replace(/[-_]/g, " "),
    message: notification.message,
    timestamp: notification.timestamp,
    read: notification.read_state,
  };
}

function getSummaryCounts(runs: ApiRun[]): SummaryCounts {
  return {
    running: runs.filter((r) => r.status === "running").length,
    queued: runs.filter((r) => r.status === "queued").length,
    failed: runs.filter((r) => r.status === "failed").length,
    completed: runs.filter((r) => r.status === "completed").length,
  };
}

function getAttentionItems(runs: ApiRun[]): AttentionItem[] {
  const items: AttentionItem[] = [];

  for (const run of runs) {
    if (run.status === "failed") {
      items.push({
        id: `failed-${run.run_id}`,
        title: `${run.name} failed`,
        message: run.error_message || "Run failed. Check logs for more detail.",
        severity: "error",
        runId: run.run_id,
      });
      continue;
    }

    if (run.status === "queued") {
      items.push({
        id: `queued-${run.run_id}`,
        title: `${run.name} is queued`,
        message: "Still waiting for execution resources.",
        severity: "warning",
        runId: run.run_id,
      });
    }
  }

  return items.slice(0, 5);
}

export default function HomePage() {
  const runsQuery = useRuns();
  const notificationsQuery = useNotifications();
  const systemQuery = useSystemStatus();

  const runs = runsQuery.data ?? [];
  const notifications = notificationsQuery.data ?? [];
  const systemStatus = systemQuery.data;

  const statusView = mapSystemStatusToView(systemStatus);
  const summaryCounts = getSummaryCounts(runs);
  const attentionItems = getAttentionItems(runs);

  const currentRuns: RunCardView[] = runs
    .filter((run) => run.status === "running" || run.status === "queued")
    .slice(0, 4)
    .map(mapRunToCardView);

  const recentAlerts: AlertView[] = notifications.slice(0, 4).map(mapNotificationToAlertView);

  const isLoading = runsQuery.isLoading || notificationsQuery.isLoading || systemQuery.isLoading;
  const hasError = runsQuery.isError || notificationsQuery.isError || systemQuery.isError;

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div>
          <p className="text-sm text-zinc-500">TAP</p>
          <h1 className="mt-1 text-2xl font-bold">Remote Experiment Control</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Check system health, triage issues, and keep an eye on active runs.
          </p>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : hasError ? (
          <EmptyState
            title="Could not load dashboard"
            description="Check the backend connection and try again."
          />
        ) : (
          <>
            <StatusStrip status={statusView} />
            <SummarySection counts={summaryCounts} />
            <NeedsAttention items={attentionItems} />
            <CurrentRuns runs={currentRuns} />
            <RecentAlerts alerts={recentAlerts} />
            <QuickActions />
          </>
        )}
      </div>
    </AppShell>
  );
}