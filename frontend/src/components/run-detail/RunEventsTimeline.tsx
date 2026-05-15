import type { RunEvent } from "@/lib/types/api";

function getEventLabel(eventType: string) {
  return eventType
    .toLowerCase()
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

function getEventTone(eventType: string) {
  const value = eventType.toLowerCase();

  if (value.includes("failed") || value.includes("error")) {
    return "border-red-800 bg-red-950 text-red-200";
  }

  if (value.includes("cancelled")) {
    return "border-yellow-800 bg-yellow-950 text-yellow-200";
  }

  if (value.includes("completed")) {
    return "border-green-800 bg-green-950 text-green-200";
  }

  if (value.includes("status")) {
    return "border-blue-800 bg-blue-950 text-blue-200";
  }

  return "border-zinc-800 bg-zinc-950 text-zinc-200";
}

export function RunEventsTimeline({ events }: { events: RunEvent[] }) { if (events.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-400">
        No run events recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <article
          key={event.event_id}
          className={`rounded-xl border p-4 ${getEventTone(event.event_type)}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">
                {getEventLabel(event.event_type)}
              </p>

              <p className="mt-1 text-sm opacity-90">{event.message}</p>

              {(event.old_status || event.new_status) && (
                <p className="mt-2 text-xs opacity-80">
                  Status: {event.old_status ?? "—"} → {event.new_status ?? "—"}
                </p>
              )}
            </div>

            <time className="shrink-0 text-xs opacity-70">
              {new Date(event.created_at).toLocaleString()}
            </time>
          </div>
        </article>
      ))}
    </div>
  );
}