"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { useCreateRun } from "@/lib/hooks/use-runs";

export default function CreateRunPage() {
  const router = useRouter();
  const createRunMutation = useCreateRun();

  const [name, setName] = useState("");
  const [gitCommit, setGitCommit] = useState("");
  const [configPath, setConfigPath] = useState("");
  const [configOverrides, setConfigOverrides] = useState("");
  const [wandbConfigRef, setWandbConfigRef] = useState("");
  const [wandbRunId, setWandbRunId] = useState("");
  const [launchNow, setLaunchNow] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  const isSubmitting = createRunMutation.isPending;

  function parseConfigOverrides(text: string) {
    const overrides: Record<string, string> = {};

    text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .forEach((line) => {
        const [key, ...valueParts] = line.split("=");
        const value = valueParts.join("=").trim();

        if (key.trim() && value) {
          overrides[key.trim()] = value;
        }
      });

    return overrides;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError("Run name is required.");
      return;
    }

    if (!configPath.trim()) {
      setFormError("Config path is required.");
      return;
    }

    try {
      const parsedOverrides = parseConfigOverrides(configOverrides);

      const createdRun = await createRunMutation.mutateAsync({
        name: name.trim(),
        git_commit: gitCommit.trim() || undefined,
        config_path: configPath.trim(),
        config_overrides:
          Object.keys(parsedOverrides).length > 0 ? parsedOverrides : undefined,
        wandb_config_ref: wandbConfigRef.trim() || undefined,
        wandb_run_id: wandbRunId.trim() || undefined,
        launch_now: launchNow,
      });

      router.push(`/runs/${createdRun.run_id}`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create run.";
      setFormError(message);
    }
  }

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm text-zinc-500">TAP</p>
          <h1 className="mt-1 text-2xl font-bold">Create Run</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Launch a new experiment from your phone or tablet.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4"
        >
          <div className="space-y-2">
            <label htmlFor="run-name" className="text-sm text-zinc-300">
              Run name
            </label>
            <input
              id="run-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-white outline-none"
              placeholder="smollm-350m-baseline"
              disabled={isSubmitting}
            />
          </div>


          <div className="space-y-2">
            <label htmlFor="git-commit" className="text-sm text-zinc-300">
              Git commit / ref
            </label>
            <input
              id="git-commit"
              value={gitCommit}
              onChange={(e) => setGitCommit(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-white outline-none"
              placeholder="optional — backend resolves current commit"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="config-path" className="text-sm text-zinc-300">
              Config path
            </label>
            <input
              id="config-path"
              value={configPath}
              onChange={(e) => setConfigPath(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-white outline-none"
              placeholder="configs/train/smollm_350m.yaml"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="config-overrides" className="text-sm text-zinc-300">
              Config overrides
            </label>
            <textarea
              id="config-overrides"
              value={configOverrides}
              onChange={(e) => setConfigOverrides(e.target.value)}
              className="min-h-28 w-full rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-white outline-none"
              placeholder={"trainer.max_steps=1000\nmodel.dim=512"}
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="wandb-config-ref" className="text-sm text-zinc-300">
              W&amp;B config ref
            </label>
            <input
              id="wandb-config-ref"
              value={wandbConfigRef}
              onChange={(e) => setWandbConfigRef(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-white outline-none"
              placeholder="optional"
              disabled={isSubmitting}
            />
          </div>


          <div className="space-y-2">
            <label htmlFor="wandb-run-id" className="text-sm text-zinc-300">
              W&amp;B run ID
            </label>
            <input
              id="wandb-run-id"
              value={wandbRunId}
              onChange={(e) => setWandbRunId(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-white outline-none"
              placeholder="optional existing W&B run ID"
              disabled={isSubmitting}
            />
          </div>

          <label className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-black px-3 py-2.5 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={launchNow}
              onChange={(e) => setLaunchNow(e.target.checked)}
              disabled={isSubmitting}
            />
            Launch on Slurm now
          </label>

          {formError ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
              {formError}
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => router.push("/runs")}
              className="rounded-xl border border-zinc-700 px-4 py-3 text-sm font-medium text-zinc-200"
              disabled={isSubmitting}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="rounded-xl bg-white px-4 py-3 text-sm font-medium text-black disabled:opacity-60"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Launching..." : "Launch Run"}
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}