import { SummaryCounts } from "@/lib/types/view";
import { SectionTitle } from "@/components/shared/section-title";

type SummarySectionProps = {
  counts: SummaryCounts;
};

export function SummarySection({ counts }: SummarySectionProps) {
  const items = [
    { label: "Running", value: counts.running },
    { label: "Queued", value: counts.queued },
    { label: "Failed", value: counts.failed },
    { label: "Completed", value: counts.completed },
  ];

  return (
    <section>
      <SectionTitle title="Overview" />
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
            <p className="text-xs text-zinc-500">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}