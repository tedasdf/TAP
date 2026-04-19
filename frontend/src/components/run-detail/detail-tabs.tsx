"use client";

import { cn } from "@/lib/utils";

export type RunDetailTab = "overview" | "metrics" | "logs" | "job" | "config";

type DetailTabsProps = {
  activeTab: RunDetailTab;
  onChange: (tab: RunDetailTab) => void;
};

const tabs: RunDetailTab[] = ["overview", "metrics", "logs", "job", "config"];

export function DetailTabs({ activeTab, onChange }: DetailTabsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange(tab)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm capitalize whitespace-nowrap",
            activeTab === tab
              ? "border-white bg-white text-black"
              : "border-zinc-700 bg-zinc-900 text-zinc-300",
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}