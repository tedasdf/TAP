import { cn } from "@/lib/utils";
import { HealthState, RunStatus } from "@/lib/types/view";

type StatusBadgeProps = {
  status: RunStatus | HealthState;
};

const statusStyles: Record<string, string> = {
  created: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
  running: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  queued: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  failed: "bg-red-500/15 text-red-300 border-red-500/30",
  completed: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  cancelled: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",

  healthy: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  connected: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  degraded: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  disconnected: "bg-red-500/15 text-red-300 border-red-500/30",
  unknown: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium capitalize",
        statusStyles[status] ?? statusStyles.unknown,
      )}
    >
      {status}
    </span>
  );
}