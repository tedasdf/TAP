"use client";

import { useState } from "react";

type LogsTabProps = {
  logs: string[];
};

export function LogsTab({ logs }: LogsTabProps) {
  const [wrap, setWrap] = useState(true);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/70 p-3">
        <p className="text-sm text-zinc-300">Recent logs</p>
        <button
          type="button"
          onClick={() => setWrap((prev) => !prev)}
          className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-200"
        >
          {wrap ? "Disable wrap" : "Enable wrap"}
        </button>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-black p-4">
        <pre
          className={`max-h-[28rem] overflow-auto text-xs leading-6 text-zinc-200 ${
            wrap ? "whitespace-pre-wrap break-words" : "whitespace-pre"
          }`}
        >
          {logs.join("\n")}
        </pre>
      </div>
    </div>
  );
}