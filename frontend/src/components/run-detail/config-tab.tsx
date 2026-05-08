type ConfigTabProps = {
  configPath: string;
  configOverrides?: string;
  gitCommit?: string | null;
  wandbRunId?: string | null;
};

export function ConfigTab({
  configPath,
  configOverrides,
  gitCommit,
  wandbRunId,
}: ConfigTabProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Config Path</h3>
        <p className="mt-3 text-sm text-zinc-300 break-words">{configPath}</p>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Config Overrides</h3>
        <pre className="mt-3 whitespace-pre-wrap break-words text-sm text-zinc-300">
          {configOverrides || "No overrides"}
        </pre>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">References</h3>

        <div className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Git Commit</span>
            <span className="text-right text-zinc-200">{gitCommit ?? "—"}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">W&B Run ID</span>
            <span className="text-right text-zinc-200">{wandbRunId ?? "—"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}