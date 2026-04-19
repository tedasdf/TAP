import { RunCardView } from "@/lib/types/view";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionTitle } from "@/components/shared/section-title";
import { RunCard } from "@/components/runs/run-card";

type CurrentRunsProps = {
  runs: RunCardView[];
};

export function CurrentRuns({ runs }: CurrentRunsProps) {
  return (
    <section>
      <SectionTitle title="Current Runs" subtitle="Running and queued experiments." />

      {runs.length === 0 ? (
        <EmptyState title="No active runs" description="Nothing is running or queued right now." />
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </div>
      )}
    </section>
  );
}