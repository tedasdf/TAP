import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import { AlertView } from "@/lib/types/view";

type AlertCardProps = {
  alert: AlertView;
};

const iconMap = {
  info: Info,
  warning: TriangleAlert,
  error: AlertCircle,
  success: CheckCircle2,
};

const colorMap = {
  info: "text-blue-300",
  warning: "text-amber-300",
  error: "text-red-300",
  success: "text-emerald-300",
};

export function AlertCard({ alert }: AlertCardProps) {
  const Icon = iconMap[alert.type];

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${colorMap[alert.type]}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-medium text-white">{alert.title}</h3>
            {!alert.read ? (
              <span className="h-2 w-2 rounded-full bg-blue-400" />
            ) : null}
          </div>
          <p className="mt-1 text-sm text-zinc-300">{alert.message}</p>
          <p className="mt-2 text-xs text-zinc-500">{alert.timestamp}</p>
        </div>
      </div>
    </div>
  );
}