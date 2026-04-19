import Link from "next/link";
import { AlertView } from "@/lib/types/view";
import { AlertCard } from "@/components/alerts/alert-card";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionTitle } from "@/components/shared/section-title";

type RecentAlertsProps = {
  alerts: AlertView[];
};

export function RecentAlerts({ alerts }: RecentAlertsProps) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <SectionTitle title="Recent Alerts" />
        <Link href="/alerts" className="text-sm text-zinc-400 hover:text-white">
          View all
        </Link>
      </div>

      {alerts.length === 0 ? (
        <EmptyState title="No recent alerts" />
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </section>
  );
}