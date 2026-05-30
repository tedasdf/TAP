"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check, ChevronDown, ChevronUp, GitBranch, Rocket } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useCreateTemplate, useLaunchTemplate } from "@/lib/hooks/use-templates";
import type { ParamSpec } from "@/lib/types/api";
import { cn } from "@/lib/utils";

// ─── Registry ───────────────────────────────────────────────────────────────

type ParamDef = {
  key: string;
  label: string;
  section: "model" | "training" | "data";
  options: (string | number)[];
  canDerive: boolean;
  deriveExpr?: string; // uses full dotted key as variable name
  deriveFrom?: string; // full dotted key of parent param
};

const PARAMS: ParamDef[] = [
  {
    key: "model.attention_type", label: "attention_type", section: "model",
    options: ["baseline", "gqa", "mha"], canDerive: false,
  },
  {
    key: "model.normalization", label: "normalization", section: "model",
    options: ["rmsnorm", "layernorm", "none"], canDerive: false,
  },
  {
    key: "model.mlp_type", label: "mlp_type", section: "model",
    options: ["gelu", "silu", "relu"], canDerive: false,
  },
  {
    key: "model.d_model", label: "d_model", section: "model",
    options: [128, 256, 512, 1024], canDerive: false,
  },
  {
    key: "model.n_heads", label: "n_heads", section: "model",
    options: [2, 4, 8, 16], canDerive: true,
    deriveExpr: "model.d_model / 64", deriveFrom: "model.d_model",
  },
  {
    key: "model.n_layers", label: "n_layers", section: "model",
    options: [2, 4, 6, 8, 12], canDerive: false,
  },
  {
    key: "training.learning_rate", label: "learning_rate", section: "training",
    options: [3e-4, 1e-4, 3e-5, 1e-5], canDerive: false,
  },
  {
    key: "training.batch_size", label: "batch_size", section: "training",
    options: [4, 8, 16, 32], canDerive: true,
    deriveExpr: "model.d_model / 64", deriveFrom: "model.d_model",
  },
  {
    key: "training.max_steps", label: "max_steps", section: "training",
    options: [100, 500, 1000, 5000, 10000], canDerive: false,
  },
  {
    key: "training.scheduler", label: "scheduler", section: "training",
    options: ["cosine", "linear", "constant"], canDerive: false,
  },
  {
    key: "data.source_type", label: "source_type", section: "data",
    options: ["huggingface", "local"], canDerive: false,
  },
  {
    key: "data.dataset_name", label: "dataset_name", section: "data",
    options: ["HuggingFaceFW/fineweb-edu", "openwebtext", "wikitext-103"], canDerive: false,
  },
];

const SECTIONS: { id: "model" | "training" | "data"; label: string }[] = [
  { id: "model", label: "Model Architecture" },
  { id: "training", label: "Training" },
  { id: "data", label: "Data" },
];

// ─── State ───────────────────────────────────────────────────────────────────

type Role = "fixed" | "vary" | "derive";

type ParamState = {
  role: Role;
  fixedValue: string | number;
  varyValues: (string | number)[];
};

function initState(): Record<string, ParamState> {
  return Object.fromEntries(
    PARAMS.map((p) => [p.key, { role: "fixed" as Role, fixedValue: p.options[0], varyValues: [] }]),
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(v: string | number): string {
  if (typeof v === "string") return v;
  if (!Number.isFinite(v)) return "—";
  if (Number.isInteger(v)) return String(v);
  if (Math.abs(v) < 0.1 && v !== 0) return v.toExponential();
  return String(v);
}

// Only used for registry-defined expressions — not user input.
function evalSimple(expr: string, fromKey: string, fromValue: number): number {
  const substituted = expr.replace(fromKey, String(fromValue));
  try {
    // eslint-disable-next-line no-new-func
    return Function(`"use strict"; return (${substituted})`)() as number;
  } catch {
    return NaN;
  }
}

type ComboRow = Record<string, string | number>;

function computeMatrix(state: Record<string, ParamState>): ComboRow[] {
  const varyDefs = PARAMS.filter(
    (p) => state[p.key].role === "vary" && state[p.key].varyValues.length > 0,
  );
  if (varyDefs.length === 0) return [];

  let combos: ComboRow[] = [{}];
  for (const p of varyDefs) {
    combos = combos.flatMap((c) =>
      state[p.key].varyValues.map((v) => ({ ...c, [p.key]: v })),
    );
  }

  for (const p of PARAMS) {
    const s = state[p.key];
    if (s.role === "fixed") {
      for (const c of combos) c[p.key] = s.fixedValue;
    } else if (s.role === "derive" && p.deriveExpr && p.deriveFrom) {
      for (const c of combos) {
        const from = c[p.deriveFrom];
        c[p.key] = typeof from === "number" ? evalSimple(p.deriveExpr, p.deriveFrom, from) : "—";
      }
    }
  }
  return combos;
}

function compileParams(state: Record<string, ParamState>): Record<string, ParamSpec> {
  const result: Record<string, ParamSpec> = {};
  for (const p of PARAMS) {
    const s = state[p.key];
    if (s.role === "fixed") {
      result[p.key] = { role: "fixed", value: s.fixedValue };
    } else if (s.role === "vary") {
      result[p.key] = { role: "vary", values: s.varyValues };
    } else if (s.role === "derive" && p.deriveExpr && p.deriveFrom) {
      result[p.key] = { role: "derive", expr: p.deriveExpr, from: p.deriveFrom };
    }
  }
  return result;
}

// ─── Components ──────────────────────────────────────────────────────────────

function RoleToggle({
  def,
  role,
  onChange,
}: {
  def: ParamDef;
  role: Role;
  onChange: (r: Role) => void;
}) {
  const options: { id: Role; label: string }[] = [
    { id: "fixed", label: "Fixed" },
    { id: "vary", label: "Vary" },
    ...(def.canDerive ? [{ id: "derive" as Role, label: "Derive" }] : []),
  ];
  return (
    <div className="flex overflow-hidden rounded-lg border border-zinc-700 bg-zinc-800/50">
      {options.map((o, i) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onChange(o.id)}
          className={cn(
            "flex-1 min-h-[44px] px-2.5 text-xs font-medium transition",
            i > 0 && "border-l border-zinc-700",
            role === o.id ? "bg-white text-black" : "text-zinc-400 hover:text-zinc-100",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ParamCard({
  def,
  state,
  allState,
  onChange,
  disabled,
}: {
  def: ParamDef;
  state: ParamState;
  allState: Record<string, ParamState>;
  onChange: (patch: Partial<ParamState>) => void;
  disabled: boolean;
}) {
  function setRole(role: Role) {
    const patch: Partial<ParamState> = { role };
    if (role === "vary" && state.varyValues.length === 0) {
      patch.varyValues = [def.options[0]];
    }
    onChange(patch);
  }

  function toggleVary(v: string | number) {
    const cur = state.varyValues;
    if (cur.includes(v)) {
      if (cur.length === 1) return; // enforce at least one
      onChange({ varyValues: cur.filter((x) => x !== v) });
    } else {
      onChange({ varyValues: [...cur, v] });
    }
  }

  const fromDef = def.deriveFrom ? PARAMS.find((p) => p.key === def.deriveFrom) : undefined;
  const fromState = def.deriveFrom ? allState[def.deriveFrom] : undefined;
  const fromValues =
    fromState?.role === "vary"
      ? fromState.varyValues
      : fromState
        ? [fromState.fixedValue]
        : [];

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <code className="font-mono text-sm font-medium text-zinc-100">{def.label}</code>
        <div className={cn("shrink-0", def.canDerive ? "w-52" : "w-36")}>
          <RoleToggle def={def} role={state.role} onChange={disabled ? () => {} : setRole} />
        </div>
      </div>

      {state.role === "fixed" && (
        <div className="flex flex-wrap gap-2">
          {def.options.map((opt) => (
            <button
              key={String(opt)}
              type="button"
              disabled={disabled}
              onClick={() => onChange({ fixedValue: opt })}
              className={cn(
                "min-h-[44px] px-3 rounded-lg border text-sm transition",
                state.fixedValue === opt
                  ? "border-white/40 bg-white/10 text-white"
                  : "border-zinc-700 bg-zinc-800/40 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200",
              )}
            >
              {fmt(opt)}
            </button>
          ))}
        </div>
      )}

      {state.role === "vary" && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {def.options.map((opt) => {
              const on = state.varyValues.includes(opt);
              return (
                <button
                  key={String(opt)}
                  type="button"
                  disabled={disabled}
                  onClick={() => toggleVary(opt)}
                  className={cn(
                    "inline-flex items-center gap-1.5 min-h-[44px] px-3 rounded-lg border text-sm transition",
                    on
                      ? "border-blue-500/40 bg-blue-500/15 text-blue-100"
                      : "border-zinc-700 bg-zinc-800/40 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200",
                  )}
                >
                  {on && <Check className="h-3.5 w-3.5 shrink-0" />}
                  {fmt(opt)}
                </button>
              );
            })}
          </div>
          {state.varyValues.length === 0 && (
            <p className="text-xs text-amber-400">Select at least one value.</p>
          )}
        </div>
      )}

      {state.role === "derive" && def.deriveExpr && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800/40 px-3 py-2">
            <span className="shrink-0 text-xs text-zinc-500">expr</span>
            <code className="font-mono text-sm text-amber-300">{def.deriveExpr}</code>
          </div>
          {fromValues.length > 0 ? (
            <div className="overflow-hidden rounded-lg border border-zinc-700">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-700 bg-zinc-800/60">
                    <th className="px-3 py-2 text-left font-medium text-zinc-400">
                      {fromDef?.label ?? def.deriveFrom}
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-zinc-400">
                      {def.label}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {fromValues.map((v) => (
                    <tr key={String(v)} className="border-b border-zinc-800 last:border-0">
                      <td className="px-3 py-2 font-mono text-zinc-200">{fmt(v)}</td>
                      <td className="px-3 py-2 font-mono text-zinc-200">
                        {typeof v === "number"
                          ? fmt(evalSimple(def.deriveExpr!, def.deriveFrom!, v))
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-zinc-500">
              Set{" "}
              <code className="font-mono text-zinc-300">{fromDef?.label ?? def.deriveFrom}</code>{" "}
              to Vary to see example values.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function MatrixPreview({ matrix }: { matrix: ComboRow[] }) {
  const [open, setOpen] = useState(false);

  const varyKeys = useMemo(() => {
    if (matrix.length < 2) return Object.keys(matrix[0] ?? {});
    const first = matrix[0];
    return Object.keys(first).filter((k) => matrix.some((r) => r[k] !== first[k]));
  }, [matrix]);

  if (matrix.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 p-4 text-center text-sm text-zinc-500">
        Set at least one parameter to Vary to see the run matrix.
      </div>
    );
  }

  const preview = matrix.slice(0, 5);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3"
      >
        <div className="flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-zinc-400" />
          <span className="text-sm text-zinc-200">
            <span className="font-semibold text-blue-400">{matrix.length}</span>{" "}
            run{matrix.length !== 1 ? "s" : ""}
          </span>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-zinc-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-zinc-500" />
        )}
      </button>

      {open && (
        <div className="space-y-2 border-t border-zinc-800 p-3">
          {preview.map((row, i) => (
            <div key={i} className="flex flex-wrap items-center gap-1.5">
              <span className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-xs text-zinc-500">
                #{i}
              </span>
              {varyKeys.map((k) => (
                <span
                  key={k}
                  className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 font-mono text-xs text-zinc-300"
                >
                  {k.split(".").pop()}={fmt(row[k])}
                </span>
              ))}
            </div>
          ))}
          {matrix.length > 5 && (
            <p className="text-xs text-zinc-500">+{matrix.length - 5} more rows</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function NewTemplatePage() {
  const router = useRouter();
  const createMutation = useCreateTemplate();
  const launchMutation = useLaunchTemplate();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [paramState, setParamState] = useState<Record<string, ParamState>>(initState);
  const [formError, setFormError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("tap_template_seed");
    if (!raw) return;
    sessionStorage.removeItem("tap_template_seed");
    try {
      const seed = JSON.parse(raw) as Record<string, unknown>;
      setParamState((prev) => {
        const next = { ...prev };
        for (const p of PARAMS) {
          const v = seed[p.key];
          if (v === undefined || v === null) continue;
          const coerced = typeof v === "string" || typeof v === "number" ? v : String(v);
          if (p.options.map(String).includes(String(coerced))) {
            next[p.key] = { ...next[p.key], role: "fixed", fixedValue: coerced };
          }
        }
        return next;
      });
    } catch {
      // ignore malformed seed
    }
  }, []);

  function updateParam(key: string, patch: Partial<ParamState>) {
    setParamState((prev) => ({ ...prev, [key]: { ...prev[key], ...patch } }));
    setTouched(true);
  }

  const matrix = useMemo(() => computeMatrix(paramState), [paramState]);
  const compiled = useMemo(() => compileParams(paramState), [paramState]);

  const hasVary = Object.values(paramState).some(
    (s) => s.role === "vary" && s.varyValues.length > 0,
  );
  const hasEmptyVary = Object.values(paramState).some(
    (s) => s.role === "vary" && s.varyValues.length === 0,
  );
  const isBusy = createMutation.isPending || launchMutation.isPending;
  const canSubmit = name.trim().length > 0 && hasVary && !hasEmptyVary && !isBusy;

  async function doCreate() {
    return createMutation.mutateAsync({
      name: name.trim(),
      description: description.trim() || null,
      params: compiled,
    });
  }

  async function handleSave(e: React.SyntheticEvent) {
    e.preventDefault();
    setTouched(true);
    if (!canSubmit) return;
    setFormError(null);
    try {
      const tpl = await doCreate();
      router.push(`/templates/${tpl.template_id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create template.");
    }
  }

  async function handleSaveAndLaunch() {
    setTouched(true);
    if (!canSubmit) return;
    setFormError(null);
    try {
      const tpl = await doCreate();
      await launchMutation.mutateAsync({ templateId: tpl.template_id });
      router.push(`/templates/${tpl.template_id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed.");
    }
  }

  const showNoVaryError = touched && !hasVary && !hasEmptyVary;
  const showEmptyVaryError = touched && hasEmptyVary;

  return (
    <AppShell>
      <div className="space-y-6 pb-36">
        {/* Header */}
        <div>
          <Link
            href="/templates"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Templates
          </Link>
          <h1 className="mt-3 text-2xl font-bold">New Template</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Define vary axes for an experiment sweep.
          </p>
        </div>

        {/* Metadata */}
        <form id="template-form" onSubmit={handleSave} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="tpl-name" className="text-sm text-zinc-300">
              Name <span className="text-red-400">*</span>
            </label>
            <input
              id="tpl-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Attention sweep"
              disabled={isBusy}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="tpl-desc" className="text-sm text-zinc-300">
              Description{" "}
              <span className="text-xs text-zinc-500">(optional)</span>
            </label>
            <textarea
              id="tpl-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What are you exploring?"
              rows={2}
              disabled={isBusy}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
          </div>
        </form>

        {/* Param sections */}
        {SECTIONS.map((section) => (
          <section key={section.id} className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              {section.label}
            </h2>
            <div className="space-y-3">
              {PARAMS.filter((p) => p.section === section.id).map((p) => (
                <ParamCard
                  key={p.key}
                  def={p}
                  state={paramState[p.key]}
                  allState={paramState}
                  onChange={(patch) => updateParam(p.key, patch)}
                  disabled={isBusy}
                />
              ))}
            </div>
          </section>
        ))}

        {/* Matrix preview */}
        <section className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Matrix Preview
          </h2>
          <MatrixPreview matrix={matrix} />
        </section>

        {/* Validation errors */}
        {showNoVaryError && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-200">
            Add at least one vary parameter to create an experiment.
          </div>
        )}
        {showEmptyVaryError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
            Each vary parameter must have at least one value selected.
          </div>
        )}
        {formError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
            {formError}
          </div>
        )}
      </div>

      {/* Fixed footer */}
      <div className="fixed inset-x-0 bottom-16 z-10 border-t border-zinc-800 bg-zinc-950/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-400">
            <GitBranch className="h-3.5 w-3.5" />
            {matrix.length} run{matrix.length !== 1 ? "s" : ""}
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              form="template-form"
              disabled={!canSubmit}
              className="rounded-xl border border-zinc-700 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:bg-zinc-800 disabled:opacity-40"
            >
              {createMutation.isPending && !launchMutation.isPending ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={handleSaveAndLaunch}
              disabled={!canSubmit}
              className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2.5 text-sm font-medium text-black transition hover:bg-zinc-200 disabled:opacity-40"
            >
              <Rocket className="h-4 w-4" />
              {launchMutation.isPending ? "Launching…" : "Save + Launch"}
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
