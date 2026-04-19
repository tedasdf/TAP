"use client";

import { cn } from "@/lib/utils";
import { RunStatus } from "@/lib/types/view";

type FilterValue = "all" | RunStatus;

type RunFiltersProps = {
  value: FilterValue;
  onChange: (value: FilterValue) => void;
};

const filters: FilterValue[] = ["all", "running", "queued", "failed", "completed"];

export function RunFilters({ value, onChange }: RunFiltersProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {filters.map((filter) => (
        <button
          key={filter}
          type="button"
          onClick={() => onChange(filter)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm capitalize whitespace-nowrap",
            value === filter
              ? "border-white bg-white text-black"
              : "border-zinc-700 bg-zinc-900 text-zinc-300",
          )}
        >
          {filter}
        </button>
      ))}
    </div>
  );
}