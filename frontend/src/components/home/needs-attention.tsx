import Link from "next/link";
import { AttentionItem } from "@/lib/types/view";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionTitle } from "@/components/shared/section-title";

type NeedsAttentionProps = {
  items: AttentionItem[];
};

export function NeedsAttention({ items }: NeedsAttentionProps) {
  return (
    <section>
      <SectionTitle title="Needs Attention" subtitle="Runs or issues that likely need action soon." />

      {items.length === 0 ? (
        <EmptyState title="Nothing needs attention" description="Everything looks stable right now." />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className={`rounded-2xl border p-4 ${
                item.severity === "error"
                  ? "border-red-500/20 bg-red-500/10"
                  : "border-amber-500/20 bg-amber-500/10"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                  <p className="mt-1 text-sm text-zinc-300">{item.message}</p>
                </div>
                {item.runId ? (
                  <Link
                    href={`/runs/${item.runId}`}
                    className="shrink-0 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-200"
                  >
                    Open
                  </Link>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}