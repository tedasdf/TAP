import { useEffect, useState } from "react";
import { getRunLogs } from "@/lib/api/runs";
import type { ApiRunLogs, ApiRunLogFile } from "@/lib/types/api";

function LogPanel({
  title,
  log,
}: {
  title: string;
  log: ApiRunLogFile;
}) {
  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-zinc-100">{title}</h3>

        {log.path && (
          <p className="mt-1 break-words text-xs text-zinc-500">{log.path}</p>
        )}
      </div>

      {!log.exists && (
        <p className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-400">
          {log.error ?? "Log file is not available yet."}
        </p>
      )}

      {log.exists && (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-800 bg-black p-3 text-xs text-zinc-300">
          {log.content || "Log file is empty."}
        </pre>
      )}
    </section>
  );
}

export function RunLogsTab({ runId }: { runId: string }) {
  const [logs, setLogs] = useState<ApiRunLogs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let isActive = true;

    void getRunLogs(runId)
      .then((data) => {
        if (isActive) {
          setLogs(data);
          setError(null);
        }
      })
      .catch(() => {
        if (isActive) {
          setError("Could not load run logs.");
        }
      });

    return () => {
      isActive = false;
    };
  }, [runId, refreshKey]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Logs</h2>
          <p className="text-sm text-zinc-400">
            Latest Slurm stdout and stderr output.
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

      {!logs && !error && (
        <p className="text-sm text-zinc-400">Loading logs...</p>
      )}

      {logs && (
        <div className="space-y-4">
          <p className="text-xs text-zinc-500">
            Job ID: {logs.job_id ?? "No Slurm job attached"}
          </p>

          <LogPanel title="stdout" log={logs.stdout} />
          <LogPanel title="stderr" log={logs.stderr} />
        </div>
      )}
    </div>
  );
}