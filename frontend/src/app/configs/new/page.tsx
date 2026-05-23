"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  ChevronDown,
  Clipboard,
  Cpu,
  Database,
  FileCode2,
  Rocket,
  Sparkles,
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { apiRequest } from "@/lib/api/client";
import {
  defaultParams,
  formatValue,
  generateYaml,
  slmRegistry,
  type ParamMap,
  type ParamValue,
} from "@/lib/slm-registry";

type SectionKey = "model" | "training" | "data";

const SECTIONS: {
  key: SectionKey;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  fields: { key: string; label: string }[];
}[] = [
  {
    key: "model", title: "Model Architecture", icon: Cpu,
    fields: [
      { key: "attention_type", label: "attention_type" },
      { key: "d_model", label: "d_model" },
      { key: "n_heads", label: "n_heads" },
      { key: "n_layers", label: "n_layers" },
      { key: "seq_len", label: "seq_len" },
      { key: "normalization", label: "normalization" },
      { key: "mlp_type", label: "mlp_type" },
    ],
  },
  {
    key: "training", title: "Training", icon: Sparkles,
    fields: [
      { key: "learning_rate", label: "learning_rate" },
      { key: "batch_size", label: "batch_size" },
      { key: "max_steps", label: "max_steps" },
      { key: "scheduler", label: "scheduler" },
      { key: "optimizer", label: "optimizer" },
    ],
  },
  {
    key: "data", title: "Data", icon: Database,
    fields: [
      { key: "source_type", label: "source_type" },
      { key: "dataset_name", label: "dataset_name" },
      { key: "dataset_config_name", label: "dataset_config" },
    ],
  },
];

export default function ConfigBuilderPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [params, setParams] = useState<ParamMap>(defaultParams);
  const [open, setOpen] = useState({ model: true, training: true, data: true, yaml: true });
  const [yaml, setYaml] = useState(() => generateYaml("", defaultParams));
  const [copied, setCopied] = useState(false);
  const [savedPath, setSavedPath] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: (vars: { name: string; params: ParamMap }) =>
      apiRequest<{ yaml: string; path: string }>("/configs/save/slm", {
        method: "POST",
        body: JSON.stringify(vars),
      }),
  });

  // Instant client-side YAML update — no API round-trip needed
  useEffect(() => {
    setYaml(generateYaml(name, params));
  }, [name, params]);

  const canSave = name.trim().length > 0 && !saveMutation.isPending;

  function setParam(key: string, value: ParamValue) {
    setParams((p) => ({ ...p, [key]: value }));
    setSavedPath(null);
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* noop */ }
  }

  function doSave(): Promise<string | null> {
    if (!canSave) return Promise.resolve(null);
    setSavedPath(null);
    return new Promise((resolve) => {
      saveMutation.mutate(
        { name, params },
        {
          onSuccess: (d) => { setSavedPath(d.path); resolve(d.path); },
          onError: () => resolve(null),
        },
      );
    });
  }

  async function handleSaveAndLaunch() {
    const path = await doSave();
    if (path) router.push(`/runs/new?configPath=${encodeURIComponent(path)}`);
  }

  return (
    <AppShell>
      <div className="space-y-4 pb-32">
        <div>
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
          <h1 className="mt-3 text-2xl font-bold">Config Builder</h1>
          <p className="mt-2 text-sm text-zinc-400">Generate a valid SLM training YAML.</p>
        </div>

        {/* Experiment name */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Experiment name
          </label>
          <input
            value={name}
            onChange={(e) => { setName(e.target.value); setSavedPath(null); }}
            placeholder="smollm-256d-baseline"
            className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
          />
          {!name.trim() && (
            <p className="mt-1.5 text-xs text-zinc-500">Required to save.</p>
          )}
        </div>

        {/* Parameter sections */}
        {SECTIONS.map((section) => {
          const Icon = section.icon;
          const isOpen = open[section.key];
          const sectionRegistry = slmRegistry[section.key] as Record<string, { options: ParamValue[] }>;

          return (
            <section key={section.key} className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900/70">
              <button
                type="button"
                onClick={() => setOpen((o) => ({ ...o, [section.key]: !o[section.key] }))}
                className="flex w-full items-center justify-between gap-2 px-4 py-3 transition hover:bg-zinc-900"
              >
                <span className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-zinc-400" />
                  <span className="text-sm font-semibold text-zinc-100">{section.title}</span>
                </span>
                <ChevronDown className={`h-4 w-4 text-zinc-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
              </button>

              {isOpen && (
                <div className="divide-y divide-zinc-800/70 border-t border-zinc-800">
                  {section.fields.map((f) => {
                    const fullKey = `${section.key}.${f.key}`;
                    const value = params[fullKey];
                    const options = sectionRegistry[f.key]?.options ?? [];

                    return (
                      <div key={fullKey} className="flex items-center justify-between gap-3 px-4 py-2.5">
                        <span className="font-mono text-xs text-zinc-400">{f.label}</span>
                        <select
                          value={String(value)}
                          onChange={(e) => {
                            const raw = e.target.value;
                            const match = options.find((o) => String(o) === raw);
                            setParam(fullKey, match ?? raw);
                          }}
                          className="min-w-28 rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1.5 text-right font-mono text-sm text-zinc-100 focus:border-zinc-600 focus:outline-none"
                        >
                          {options.map((o) => (
                            <option key={String(o)} value={String(o)}>{formatValue(o)}</option>
                          ))}
                        </select>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          );
        })}

        {/* YAML preview */}
        <section className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900/70">
          <div className="flex items-center justify-between gap-2 px-4 py-3">
            <button
              type="button"
              onClick={() => setOpen((o) => ({ ...o, yaml: !o.yaml }))}
              className="flex flex-1 items-center gap-2"
            >
              <FileCode2 className="h-4 w-4 text-zinc-400" />
              <span className="text-sm font-semibold text-zinc-100">YAML Preview</span>
              <ChevronDown className={`ml-auto h-4 w-4 text-zinc-500 transition-transform ${open.yaml ? "rotate-180" : ""}`} />
            </button>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Clipboard className="h-3.5 w-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>

          {open.yaml && (
            <div className="border-t border-zinc-800 bg-black/40 p-3">
              <pre className="max-h-72 overflow-auto whitespace-pre font-mono text-xs leading-relaxed text-zinc-200">
                {yaml}
              </pre>
            </div>
          )}
        </section>

        {/* Saved banner */}
        {savedPath && (
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
            <div className="flex items-start gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-emerald-100">Config saved</p>
                <code className="mt-0.5 block break-all font-mono text-xs text-emerald-200/90">{savedPath}</code>
                <Link
                  href={`/runs/new?configPath=${encodeURIComponent(savedPath)}`}
                  className="mt-2 inline-flex items-center gap-1 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-100 hover:bg-emerald-500/20"
                >
                  Use in Run <Rocket className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>
        )}

        {saveMutation.isError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
            Failed to save config. Check the backend connection.
          </div>
        )}
      </div>

      {/* Sticky footer */}
      <div className="fixed inset-x-0 bottom-16 z-10 border-t border-zinc-800 bg-zinc-950/90 px-4 py-3 backdrop-blur">
        <div className="mx-auto grid max-w-3xl grid-cols-3 gap-2">
          <button type="button" onClick={() => router.back()}
            className="rounded-xl border border-zinc-700 py-2.5 text-sm font-medium text-zinc-200">
            Cancel
          </button>
          <button type="button" disabled={!canSave} onClick={doSave}
            className="rounded-xl border border-zinc-700 py-2.5 text-sm font-medium text-zinc-100 disabled:opacity-40">
            {saveMutation.isPending ? "Saving…" : "Save"}
          </button>
          <button type="button" disabled={!canSave} onClick={handleSaveAndLaunch}
            className="inline-flex items-center justify-center gap-1 rounded-xl bg-white py-2.5 text-sm font-semibold text-black disabled:opacity-40">
            Save & Launch <Rocket className="h-4 w-4" />
          </button>
        </div>
      </div>
    </AppShell>
  );
}
