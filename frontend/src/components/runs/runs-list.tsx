import { RunCardView } from "@/lib/types/view";
import { RunCard } from "@/components/runs/run-card";
import { EmptyState } from "@/components/shared/empty-state";

export function RunsList({ runs }: { runs: RunCardView[] }) {
  if (runs.length === 0) {
    return <EmptyState title="No runs found" description="Try changing your search or filter." />;
  }

  return (
    <div className="space-y-3">
      {runs.map((run) => (
        <RunCard key={run.id} run={run} />
      ))}
    </div>
  );
}