"use client";

import { useRouter } from "next/navigation";
import { LayoutTemplate } from "lucide-react";
import yaml from "js-yaml";

type ConfigTabProps = {
  configPath: string;
  configOverrides?: Record<string, unknown> | null;
  gitCommit?: string | null;
  wandbRunId?: string | null;
  configSnapshot?: Record<string, unknown> | null;
};

function flattenObject(obj: Record<string, unknown>, prefix = ""): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      Object.assign(result, flattenObject(v as Record<string, unknown>, key));
    } else {
      result[key] = v;
    }
  }
  return result;
}

export function ConfigTab({
  configPath,
  configOverrides,
  gitCommit,
  wandbRunId,
  configSnapshot,
}: ConfigTabProps) {
  const router = useRouter();

  function handleUseAsTemplate() {
    const yamlContent = (configSnapshot?.config_file as { content?: string } | undefined)?.content;
    if (yamlContent) {
      try {
        const parsed = yaml.load(yamlContent) as Record<string, unknown>;
        if (parsed && typeof parsed === "object") {
          const flat = flattenObject(parsed);
          sessionStorage.setItem("tap_template_seed", JSON.stringify(flat));
          router.push("/templates/new");
          return;
        }
      } catch {
        // fall through to config overrides
      }
    }
    const source = configOverrides;
    if (source) {
      const flat = flattenObject(source);
      sessionStorage.setItem("tap_template_seed", JSON.stringify(flat));
    }
    router.push("/templates/new");
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Config Path</h3>
        <p className="mt-3 text-sm text-zinc-300 break-words">{configPath}</p>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Config Overrides</h3>
        <pre className="mt-3 whitespace-pre-wrap break-words text-sm text-zinc-300">
          {configOverrides
            ? JSON.stringify(configOverrides, null, 2)
            : "No overrides"}
        </pre>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h3 className="text-sm font-semibold text-white">Config File</h3>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-sm text-zinc-300">
          {(configSnapshot?.config_file as { content?: string } | undefined)?.content
            ?? "No config file snapshot stored"}
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

      <button
        type="button"
        onClick={handleUseAsTemplate}
        className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-900/70 px-4 py-3 text-sm font-medium text-zinc-200 transition hover:bg-zinc-800 hover:text-white"
      >
        <LayoutTemplate className="h-4 w-4" />
        Use as Template
      </button>
    </div>
  );
}
