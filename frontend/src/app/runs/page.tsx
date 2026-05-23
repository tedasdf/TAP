"use client";

import { useMemo, useState } from "react";
import { Filter, Search } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { RunCard } from "@/components/runs/run-card";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useDeleteRun, useRuns } from "@/lib/hooks/use-runs";
import { ApiRun } from "@/lib/types/api";
import { RunCardView, RunStatus } from "@/lib/types/view";

type FilterValue = RunStatus | "all";

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
    runtime: run.runtime == null ? undefined : String(run.runtime),
    errorMessage: run.error_message ?? undefined,
    slurmJobId: run.slurm_job_id ?? undefined,
    templateId: run.template_id ?? undefined,
  };
}

export default function RunsPage() {
  const { data, isLoading, isError } = useRuns();
  const deleteRunMutation = useDeleteRun();

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<FilterValue>("all");

  const filters: Array<{ value: FilterValue; label: string }> = [
    { value: "all", label: "All" },
    { value: "running", label: "Active" },
    { value: "queued", label: "Queued" },
    { value: "failed", label: "Failed" },
    { value: "completed", label: "Completed" },
  ];

  const filteredRuns = useMemo(() => {
    const runs = data ?? [];
    const q = searchQuery.trim().toLowerCase();

    return runs
      .filter((run) => {
        const matchesSearch =
          q.length === 0
            ? true
            : run.name.toLowerCase().includes(q) ||
              run.config_path.toLowerCase().includes(q) ||
              (run.slurm_job_id ?? "").toLowerCase().includes(q);

        const matchesFilter =
          selectedFilter === "all" ? true : run.status === selectedFilter;

        return matchesSearch && matchesFilter;
      })
      .sort((a, b) => {
        const priority: Record<RunStatus, number> = {
          failed: 0,
          running: 1,
          queued: 2,
          created: 3,
          completed: 4,
          cancelled: 5,
          unknown: 6,
        };

        const statusDiff = priority[a.status] - priority[b.status];
        if (statusDiff !== 0) return statusDiff;

        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      })
      .map(mapRunToCardView);
  }, [data, searchQuery, selectedFilter]);

  return (
    <AppShell>
      <div className="pb-20">
        <div className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-950 p-4">
          <h1 className="mb-4 text-2xl font-semibold text-zinc-100">Runs</h1>

          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search runs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 py-2.5 pl-10 pr-4 text-zinc-100 placeholder-zinc-500 focus:border-zinc-700 focus:outline-none"
            />
          </div>

          <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
            {filters.map((filter) => (
              <button
                key={filter.value}
                onClick={() => setSelectedFilter(filter.value)}
                className={`flex-shrink-0 whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition-colors ${
                  selectedFilter === filter.value
                    ? "bg-blue-600 text-white"
                    : "border border-zinc-800 bg-zinc-900 text-zinc-400"
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3 p-4">
          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <EmptyState
              title="Could not load runs"
              description="Check the backend connection and try again."
            />
          ) : filteredRuns.length === 0 ? (
            <div className="py-12 text-center">
              <Filter className="mx-auto mb-3 h-12 w-12 text-zinc-700" />
              <p className="text-zinc-500">No runs found</p>
            </div>
          ) : (
            filteredRuns.map((run) => (
              <RunCard
                key={run.id}
                run={run}
                onDelete={(id) => deleteRunMutation.mutate(id)}
                isDeleting={deleteRunMutation.isPending && deleteRunMutation.variables === run.id}
              />
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}