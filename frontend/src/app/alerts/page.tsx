"use client";

import { AppShell } from "@/components/layout/app-shell";
import { AlertCard } from "@/components/alerts/alert-card";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useNotifications } from "@/lib/hooks/use-notifications";
import { ApiNotification } from "@/lib/types/api";
import { AlertView } from "@/lib/types/view";

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

export default function AlertsPage() {
  const { data, isLoading, isError } = useNotifications();

  const alerts = (data ?? [])
    .slice()
    .sort((a, b) => {
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    })
    .map(mapNotificationToAlertView);

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm text-zinc-500">TAP</p>
          <h1 className="mt-1 text-2xl font-bold">Alerts</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Recent notifications and events across runs and jobs.
          </p>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <EmptyState
            title="Could not load alerts"
            description="Check the backend connection and try again."
          />
        ) : alerts.length === 0 ? (
          <EmptyState title="No alerts" description="Nothing new right now." />
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}