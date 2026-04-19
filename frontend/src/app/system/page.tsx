"use client";

import { AppShell } from "@/components/layout/app-shell";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useSystemStatus } from "@/lib/hooks/use-system";
import { ApiSystemStatus } from "@/lib/types/api";

type SystemItem = {
  label: string;
  status: "healthy" | "connected" | "degraded" | "disconnected" | "unknown";
  note: string;
};

function normalizeStatus(
  value?: string,
): "healthy" | "connected" | "degraded" | "disconnected" | "unknown" {
  if (!value) return "unknown";

  const v = value.toLowerCase();

  if (["healthy", "ok", "up"].includes(v)) return "healthy";
  if (["connected", "reachable", "online"].includes(v)) return "connected";
  if (["degraded", "warning"].includes(v)) return "degraded";
  if (["disconnected", "down", "offline", "unreachable", "error"].includes(v)) {
    return "disconnected";
  }

  return "unknown";
}

function mapSystemStatusToItems(status?: ApiSystemStatus): SystemItem[] {
  return [
    {
      label: "Backend",
      status: normalizeStatus(status?.backend),
      note: "API health and responsiveness",
    },
    {
      label: "M3",
      status: normalizeStatus(status?.m3),
      note: "Remote execution machine connectivity",
    },
    {
      label: "Slurm",
      status: normalizeStatus(status?.slurm),
      note: "Scheduler availability and queue access",
    },
    {
      label: "Database",
      status: normalizeStatus(status?.database),
      note: "SQLite availability and persistence",
    },
    {
      label: "W&B",
      status: normalizeStatus(status?.wandb),
      note: "Experiment tracking and metric sync",
    },
  ];
}

export default function SystemPage() {
  const { data, isLoading, isError } = useSystemStatus();

  const items = mapSystemStatusToItems(data);

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm text-zinc-500">TAP</p>
          <h1 className="mt-1 text-2xl font-bold">System</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Health and connectivity for the backend and execution stack.
          </p>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <EmptyState
            title="Could not load system status"
            description="Check the backend connection and try again."
          />
        ) : (
          <>
            <div className="space-y-3">
              {items.map((item) => (
                <div
                  key={item.label}
                  className="flex items-start justify-between gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4"
                >
                  <div>
                    <h2 className="text-sm font-semibold text-white">{item.label}</h2>
                    <p className="mt-1 text-sm text-zinc-400">{item.note}</p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
              <h2 className="text-sm font-semibold text-white">Recent activity</h2>

              <div className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-zinc-500">Last Sync</span>
                  <span className="text-right text-zinc-200">{data?.last_sync ?? "—"}</span>
                </div>

                <div className="flex justify-between gap-4">
                  <span className="text-zinc-500">Last Job Launch</span>
                  <span className="text-right text-zinc-200">
                    {data?.last_job_launch ?? "—"}
                  </span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}