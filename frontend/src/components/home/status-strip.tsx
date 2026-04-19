import { StatusStripView } from "@/lib/types/view";
import { StatusBadge } from "@/components/shared/status-badge";

type StatusStripProps = {
  status: StatusStripView;
};

export function StatusStrip({ status }: StatusStripProps) {
  const items = [
    { label: "Backend", value: status.backend },
    { label: "M3", value: status.m3 },
    { label: "Slurm", value: status.slurm },
    { label: "W&B", value: status.wandb },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-3">
          <p className="mb-2 text-xs text-zinc-500">{item.label}</p>
          <StatusBadge status={item.value} />
        </div>
      ))}
    </div>
  );
}