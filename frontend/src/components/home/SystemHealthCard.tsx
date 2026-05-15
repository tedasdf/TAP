import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api/system";
import type { ApiSystemStatus } from "@/lib/types/api";

function StatusPill({ label, value }: { label: string; value?: string }) {
  const displayValue = value ?? "unknown";
  const isOk = displayValue === "ok";

  return (
    <div className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2">
      <span className="text-sm text-zinc-400">{label}</span>
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          isOk ? "bg-green-950 text-green-300" : "bg-red-950 text-red-300"
        }`}
      >
        {displayValue.toUpperCase()}
      </span>
    </div>
  );
}

export function SystemHealthCard() {
  const [health, setHealth] = useState<ApiSystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let isActive = true;

    void getHealth()
        .then((data) => {
            if (isActive) {
            setHealth(data);
            setError(null);
            }
        })
        .catch(() => {
            if (isActive) {
            setError("Could not load system health.");
            }
        });

    return () => {
      isActive = false;
    };
  }, [refreshKey]);

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">System health</h2>
          <p className="text-sm text-zinc-400">
            Basic TAP backend and database status.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setRefreshKey((value) => value + 1)}
          className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-100 hover:bg-zinc-800"
        >
          Refresh
        </button>
      </div>

      {error && (
        <p className="rounded-lg border border-red-900 bg-red-950 p-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {!health && !error && (
        <p className="text-sm text-zinc-400">Loading system health...</p>
      )}

      {health && (
        <div className="space-y-3">
          <StatusPill label="Backend" value={health.backend} />
          <StatusPill label="Database" value={health.database} />

          {health.database_error && (
            <pre className="whitespace-pre-wrap break-words rounded-lg border border-red-900 bg-red-950 p-3 text-xs text-red-300">
              {health.database_error}
            </pre>
          )}

          {health.timestamp && (
            <p className="text-xs text-zinc-500">
              Last checked: {new Date(health.timestamp).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </section>
  );
}