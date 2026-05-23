"use client";

import { useEffect } from "react";
import { GitBranch, Rocket, X } from "lucide-react";
import { useTemplatePreview } from "@/lib/hooks/use-templates";
import { cn } from "@/lib/utils";
import type { ApiRunCombo } from "@/lib/types/api";

export interface MatrixPreviewSheetProps {
  templateId: string;
  open: boolean;
  onClose: () => void;
  onLaunch: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

type Role = "vary" | "derive" | "fixed";

function inferRoles(combos: ApiRunCombo[]): Record<string, Role> {
  if (combos.length === 0) return {};
  const result: Record<string, Role> = {};
  const deriveKeys = new Set(Object.keys(combos[0].derive_trace));
  const first = combos[0].params;

  for (const key of Object.keys(first)) {
    if (deriveKeys.has(key)) {
      result[key] = "derive";
    } else if (combos.some((c) => c.params[key] !== first[key])) {
      result[key] = "vary";
    } else {
      result[key] = "fixed";
    }
  }
  return result;
}

const TAG_CLS: Record<Role, string> = {
  vary: "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
  derive: "border-amber-500/40 bg-amber-500/15 text-amber-200",
  fixed: "border-zinc-700 bg-zinc-800/60 text-zinc-400",
};

function fmt(v: string | number | undefined): string {
  if (v === undefined || v === null) return "—";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "—";
    if (Number.isInteger(v)) return String(v);
    if (Math.abs(v) < 0.1 && v !== 0) return v.toExponential();
    return String(v);
  }
  return v;
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ComboSkeleton() {
  return (
    <div className="space-y-2">
      {[72, 56, 80, 64].map((w, i) => (
        <div
          key={i}
          className="flex items-center gap-2 rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-3 py-3"
        >
          <div className="h-4 w-6 animate-pulse rounded bg-zinc-800" />
          <div className={`h-4 animate-pulse rounded-full bg-zinc-800`} style={{ width: w }} />
          <div className="h-4 w-12 animate-pulse rounded-full bg-zinc-800" />
        </div>
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function MatrixPreviewSheet({
  templateId,
  open,
  onClose,
  onLaunch,
}: MatrixPreviewSheetProps) {
  // Lock body scroll while open
  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Only fetch when open (pass empty string to disable when closed)
  const { data, isLoading } = useTemplatePreview(open ? templateId : "");

  const roles = data ? inferRoles(data.combos) : {};
  const n = data?.total_runs ?? 0;

  // Show only vary + derive columns (the interesting ones) in the row tags
  const showCols = Object.entries(roles)
    .filter(([, r]) => r !== "fixed")
    .map(([k]) => k);
  const displayCols = showCols.length > 0 ? showCols : Object.keys(roles);

  function handleLaunch() {
    onLaunch();
    onClose();
  }

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className={cn(
          "fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
      />

      {/* Sheet panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Matrix preview"
        className={cn(
          "fixed inset-x-0 bottom-0 z-50 flex max-h-[85vh] flex-col rounded-t-3xl border-t border-zinc-800 bg-zinc-950 shadow-2xl transition-transform duration-300 ease-out",
          open ? "translate-y-0" : "translate-y-full",
        )}
      >
        {/* Drag handle */}
        <div className="flex shrink-0 justify-center pt-3">
          <div className="h-1 w-10 rounded-full bg-zinc-700" />
        </div>

        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-zinc-800 px-5 py-4">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-zinc-400" />
            <h2 className="text-base font-semibold text-zinc-100">
              {isLoading
                ? "Loading matrix…"
                : `${n} run${n !== 1 ? "s" : ""} will be submitted`}
            </h2>
          </div>
          <button
            type="button"
            aria-label="Close preview"
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Legend */}
        {!isLoading && data && (
          <div className="flex shrink-0 items-center gap-3 border-b border-zinc-800/60 px-5 py-2.5">
            <span className="text-xs text-zinc-500">Legend</span>
            {(["vary", "derive", "fixed"] as Role[]).map((r) => (
              <span
                key={r}
                className={cn("rounded-full border px-2 py-0.5 text-xs", TAG_CLS[r])}
              >
                {r}
              </span>
            ))}
          </div>
        )}

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading ? (
            <ComboSkeleton />
          ) : !data || data.combos.length === 0 ? (
            <p className="text-center text-sm text-zinc-500">No combinations found.</p>
          ) : (
            <ul className="space-y-2">
              {data.combos.map((combo) => (
                <li
                  key={combo.combo_index}
                  className="flex flex-wrap items-start gap-1.5 rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-3 py-2.5"
                >
                  <span className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-xs text-zinc-500">
                    #{combo.combo_index}
                  </span>
                  {displayCols.map((k) => (
                    <span
                      key={k}
                      className={cn(
                        "rounded-full border px-2 py-0.5 font-mono text-xs",
                        TAG_CLS[roles[k] ?? "fixed"],
                      )}
                    >
                      {k.split(".").pop()}={fmt(combo.params[k])}
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t border-zinc-800 px-5 pb-8 pt-4">
          <button
            type="button"
            onClick={handleLaunch}
            disabled={isLoading || !data || n === 0}
            className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white py-3.5 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:opacity-40"
          >
            <Rocket className="h-4 w-4" />
            {isLoading ? "Loading…" : `Launch ${n} run${n !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>
    </>
  );
}
