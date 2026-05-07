type ConfigTabProps = {
  configPath: string;
  configOverrides?: string;
  configSnapshot?: Record<string, unknown> | null;
  gitCommit?: string | null;
  wandbRunId?: string | null;
};


function getNestedString(
  object: Record<string, unknown> | null | undefined,
  path: string[],
): string | null {
  let current: unknown = object;

  for (const key of path) {
    if (
      current === null ||
      typeof current !== "object" ||
      !(key in current)
    ) {
      return null;
    }

    current = (current as Record<string, unknown>)[key];
  }

  return typeof current === "string" && current.trim() ? current : null;
}

export function ConfigTab({
  configPath,
  configOverrides,
  configSnapshot,
  gitCommit,
  wandbRunId,
}: ConfigTabProps) {

  const datasetRef = getNestedString(configSnapshot, [
    "data_references",
    "dataset",
  ]);

  const tokenizerRef = getNestedString(configSnapshot, [
    "data_references",
    "tokenizer",
  ]);

  const submitScript = getNestedString(configSnapshot, [
    "launch_metadata",
    "submit_script",
  ]);

  const remoteHost = getNestedString(configSnapshot, [
    "launch_metadata",
    "remote_host",
  ]);

  const remoteRepoPath = getNestedString(configSnapshot, [
    "launch_metadata",
    "remote_repo_path",
  ]);

  const workingDirectory = getNestedString(configSnapshot, [
    "launch_metadata",
    "working_directory",
  ]);

  const wandbUrl = getNestedString(configSnapshot, ["wandb", "url"]);
  
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
        <h3 className="text-sm font-semibold text-white">
          Reproducibility Metadata
        </h3>

        <div className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Git Commit</span>
            <span className="text-right text-zinc-200 break-all">
              {gitCommit ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Dataset</span>
            <span className="text-right text-zinc-200 break-words">
              {datasetRef ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Tokenizer</span>
            <span className="text-right text-zinc-200 break-words">
              {tokenizerRef ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Submit Script</span>
            <span className="text-right text-zinc-200 break-words">
              {submitScript ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Remote Host</span>
            <span className="text-right text-zinc-200">
              {remoteHost ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Remote Repo</span>
            <span className="text-right text-zinc-200 break-words">
              {remoteRepoPath ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">Working Directory</span>
            <span className="text-right text-zinc-200 break-words">
              {workingDirectory ?? "—"}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-zinc-500">W&B</span>
            <span className="text-right text-zinc-200">
              {wandbUrl ? (
                <a
                  href={wandbUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-300 underline underline-offset-4"
                >
                  Open W&B run
                </a>
              ) : (
                "—"
              )}
            </span>
          </div>
        </div>
      </div>
      
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Config Snapshot</h3>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-black/30 p-3 text-xs text-zinc-300">
          {configSnapshot
            ? JSON.stringify(configSnapshot, null, 2)
            : "No config snapshot stored"}
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