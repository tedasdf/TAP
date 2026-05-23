# M6 — Config Builder (Lovable Design Brief)

## What this feature does

A form-based page that generates a valid SLM training YAML config. The user fills in model/training/data fields, sees a live YAML preview update as they type, then saves the config and optionally launches a run immediately.

**Route:** `/configs/new`

---

## Backend API (already built — just call these)

### `GET /registry/slm`
Returns all valid field options and compatibility rules. Call this on page load to populate every dropdown. **Never hardcode dropdown values** — always use what the registry returns.

Example response shape:
```json
{
  "model": {
    "attention_type": { "options": ["baseline", "gqa", "mha"] },
    "normalization": { "options": ["rmsnorm", "layernorm", "none"] },
    "mlp_type": { "options": ["gelu", "silu", "relu"] },
    "d_model": { "options": [128, 256, 512, 1024] },
    "n_heads": { "options": [2, 4, 8, 16] },
    "n_layers": { "options": [2, 4, 6, 8, 12] },
    "seq_len": { "options": [128, 256, 512, 1024, 2048] }
  },
  "training": {
    "learning_rate": { "options": [0.001, 0.0003, 0.0001, 0.00003] },
    "batch_size": { "options": [4, 8, 16, 32] },
    "max_steps": { "options": [100, 500, 1000, 5000, 10000] },
    "scheduler": { "options": ["cosine", "linear", "constant"] },
    "optimizer": { "options": ["adamw", "adam"] }
  },
  "data": {
    "source_type": { "options": ["huggingface", "local"] },
    "dataset_name": { "options": ["HuggingFaceFW/fineweb-edu", "openwebtext", "wikitext-103"] },
    "dataset_config_name": { "options": ["sample-10BT", "sample-100BT", "default"] }
  }
}
```

### `POST /configs/generate/slm`
Takes the filled form, returns YAML string. Call on every field change for live preview.

Request body:
```json
{
  "name": "my-experiment",
  "params": {
    "model.attention_type": "baseline",
    "model.d_model": 256,
    "model.n_heads": 4,
    "model.n_layers": 6,
    "model.seq_len": 512,
    "model.normalization": "rmsnorm",
    "model.mlp_type": "gelu",
    "training.learning_rate": 0.0003,
    "training.batch_size": 8,
    "training.max_steps": 1000,
    "training.scheduler": "cosine",
    "training.optimizer": "adamw",
    "data.source_type": "huggingface",
    "data.dataset_name": "HuggingFaceFW/fineweb-edu",
    "data.dataset_config_name": "sample-10BT"
  }
}
```

Response:
```json
{
  "yaml": "experiment:\n  name: my-experiment\n  family: slm\n..."
}
```

### `POST /configs/save/slm`
Same body as generate, but also writes the file to disk and returns the path.

Response:
```json
{
  "yaml": "...",
  "path": "generated_configs/slm/my-experiment-20260522_143000.yaml"
}
```

---

## Page Layout (mobile-first, dark zinc theme)

### Overall structure
```
┌──────────────────────────────┐
│  ← Back    Config Builder    │  ← sticky header
├──────────────────────────────┤
│  [Experiment name input]     │
├──────────────────────────────┤
│  ▼ Model Architecture        │  ← collapsible section
│    attention_type  [select]  │
│    d_model         [select]  │
│    n_heads         [select]  │
│    n_layers        [select]  │
│    seq_len         [select]  │
│    normalization   [select]  │
│    mlp_type        [select]  │
├──────────────────────────────┤
│  ▼ Training                  │
│    learning_rate   [select]  │
│    batch_size      [select]  │
│    max_steps       [select]  │
│    scheduler       [select]  │
├──────────────────────────────┤
│  ▼ Data                      │
│    source_type     [select]  │
│    dataset_name    [select]  │
│    dataset_config  [select]  │
├──────────────────────────────┤
│  ▼ YAML Preview              │  ← collapsible, monospace, scrollable
│    experiment:               │
│      name: my-experiment     │
│      ...                     │
│    [Copy] button             │
├──────────────────────────────┤
│  [Cancel]  [Save]  [Save & Launch →]  │  ← sticky footer
└──────────────────────────────┘
```

---

## Exact user flow

1. **Page loads** → `GET /registry/slm` → populates all dropdowns
2. **User types experiment name** → debounced call to `POST /configs/generate/slm` → YAML preview updates
3. **User changes any dropdown** → same debounced generate call → YAML preview updates live
4. **"Copy" button** → copies YAML text to clipboard, button shows ✓ for 2s
5. **"Save" button** → calls `POST /configs/save/slm` → shows the returned path in a success banner:
   ```
   ✓ Saved: generated_configs/slm/my-experiment-20260522_143000.yaml
   ```
6. **"Save & Launch →" button** → calls save, then navigates to `/runs/new?configPath=generated_configs/slm/my-experiment-...yaml` (the create run page should pre-fill the config path field from the query param)

---

## Component details

### Experiment name field
- Full-width text input at the top
- Placeholder: `smollm-256d-baseline`
- Required — both Save buttons disabled until non-empty

### Field selects
Each field is a labelled row:
```
label (mono, zinc-400)     [dropdown value  ▼]
```
- Dropdown shows the value, not a long label
- Numbers formatted cleanly: `3e-4` not `0.0003`, `1k` not `1000` for steps ≥ 1000

### YAML Preview panel
- Collapsible (open by default)
- Monospace font, dark bg (`bg-black/40`), scrollable up to `max-h-72`
- "Copy" button in top-right corner of the panel
- Updates within ~300ms of any field change (debounce)
- Show a subtle loading shimmer while the generate call is in-flight

### Sticky footer
Three buttons, full-width grid:
```
[Cancel]    [Save]    [Save & Launch →]
```
- Cancel: goes back (`/`)
- Save: calls `/configs/save/slm`, disabled while pending
- Save & Launch: calls save then navigates, disabled while pending
- Both save buttons disabled if name is empty

### Success banner (after Save)
Appears between the form and the footer:
```
┌─────────────────────────────────────────────┐
│ ✓ Config saved                              │
│ generated_configs/slm/my-experiment-....yaml│
│ [Use in Run →]                              │
└─────────────────────────────────────────────┘
```
`Use in Run →` navigates to `/runs/new?configPath=<path>`

---

## Design tokens (match rest of app)

- Background: `bg-zinc-950`
- Cards / sections: `rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4`
- Inputs / selects: `rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100`
- Primary button: `rounded-xl bg-white px-4 py-3 text-sm font-medium text-black`
- Secondary button: `rounded-xl border border-zinc-700 px-4 py-3 text-sm font-medium text-zinc-200`
- Icons: Lucide React
- Monospace: `font-mono`
- Success accent: `border-emerald-500/30 bg-emerald-500/10 text-emerald-200`

---

## Tech constraints

- Next.js App Router, `"use client"` page
- TanStack Query for registry fetch (`useQuery`) and generate/save (`useMutation`)
- Debounce generate calls with a 300ms delay (use `useEffect` + `setTimeout`)
- Read `?configPath=` from URL on `/runs/new` page to pre-fill the config path input
- No YAML library needed on the frontend — the backend returns the YAML string
- API base URL from `process.env.NEXT_PUBLIC_API_BASE_URL`
