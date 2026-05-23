# TAP — Mobile Design Brief for Figma

**App:** TAP (Training Automation Platform)
**Purpose:** Mobile-first web app for ML researchers to launch, monitor, and manage neural network training jobs on a remote GPU cluster.
**Target:** Single researcher. Always dark mode. Used on the go to check training runs and triage issues.

---

## 1. Color Palette

### Base
| Token | Hex | Usage |
|---|---|---|
| Background | `#000000` | Page background |
| Surface | `#09090b` | Tooltip backgrounds |
| Card | `#18181b` | Cards, inputs |
| Border | `#27272a` | All card/input borders |
| Text Primary | `#ffffff` | Headings, values |
| Text Secondary | `#a1a1aa` | Body copy |
| Text Tertiary | `#71717a` | Labels, metadata |

### Status Colors
| Status | Background | Text | Border |
|---|---|---|---|
| Running / Healthy | `#10b981` @ 15% | `#6ee7b7` | `#10b981` @ 30% |
| Queued / Degraded | `#f59e0b` @ 15% | `#fcd34d` | `#f59e0b` @ 30% |
| Failed / Error | `#ef4444` @ 10% | `#fca5a5` | `#ef4444` @ 20% |
| Completed | `#3b82f6` @ 15% | `#93c5fd` | `#3b82f6` @ 30% |
| Cancelled / Unknown | `#71717a` @ 15% | `#d4d4d8` | `#71717a` @ 30% |

### Interactive
| Element | Color |
|---|---|
| Primary button | `#ffffff` bg, `#000000` text |
| Secondary button | `#18181b` bg, `#e4e4e7` text |
| Danger button | `#ef4444` @ 10% bg, `#fca5a5` text |
| Unread dot | `#60a5fa` |
| Notification badge | `#ef4444` |

---

## 2. Typography

System font stack: `Arial, Helvetica, sans-serif` (no custom font currently).

| Role | Size | Weight | Color |
|---|---|---|---|
| Page title | 24px | Bold | `#ffffff` |
| Section heading | 16px | Semibold | `#ffffff` |
| Card title | 14px | Semibold | `#ffffff` |
| Body / label | 14px | Regular | `#a1a1aa` |
| Metadata / caption | 12px | Regular | `#71717a` |
| Status badge | 12px | Medium | (status color) |
| Metric value (large) | 20px | Semibold | `#ffffff` |
| Code / logs | 12px | Mono | `#d4d4d8` |

---

## 3. Layout & Spacing

- **Max content width:** 768px, centered
- **Horizontal padding:** 16px
- **Vertical page padding:** 24px top, 96px bottom (clears bottom nav)
- **Section gap:** 24px
- **Card gap in lists:** 12px
- **Card padding:** 12–16px
- **Card border radius:** 16px (`rounded-2xl`)
- **Input border radius:** 12px (`rounded-xl`)

---

## 4. Navigation

**Bottom navigation bar** — fixed, always visible.

```
┌──────────────────────────────────────────┐
│  🏠 Home   📂 Runs   🔔 Alerts  🖥 System │
└──────────────────────────────────────────┘
```

| Property | Value |
|---|---|
| Background | `#000000` @ 95% + backdrop blur |
| Top border | `#27272a` |
| Height | ~56px |
| Icon size | 16px |
| Label size | 12px |
| Active color | `#ffffff` |
| Inactive color | `#71717a` |

**Fixed top-right:** Notification bell icon with red unread count badge.

---

## 5. Screen Inventory

### 5.1 Dashboard (`/`)

The researcher's home base. Answers: "Is everything OK? What's running right now?"

```
┌─────────────────────────────┐
│  TAP                        │
│  Remote Experiment Control  │
│  [subtitle]                 │
├─────────────────────────────┤
│  STATUS STRIP               │
│  ┌──────┐ ┌──────┐          │
│  │ API  │ │  M3  │          │
│  └──────┘ └──────┘          │
│  ┌──────┐ ┌──────┐          │
│  │ SLRM │ │ W&B  │          │
│  └──────┘ └──────┘          │
├─────────────────────────────┤
│  SUMMARY                    │
│  ┌────────┐ ┌────────┐      │
│  │   2    │ │   1    │      │
│  │Running │ │Queued  │      │
│  └────────┘ └────────┘      │
│  ┌────────┐ ┌────────┐      │
│  │   0    │ │  14    │      │
│  │ Failed │ │  Done  │      │
│  └────────┘ └────────┘      │
├─────────────────────────────┤
│  NEEDS ATTENTION             │
│  [red/amber alert cards]     │
├─────────────────────────────┤
│  CURRENT RUNS                │
│  [run cards, max 4]          │
├─────────────────────────────┤
│  RECENT ALERTS       View all│
│  [alert cards, max 4]        │
├─────────────────────────────┤
│  QUICK ACTIONS               │
│  ┌────────┐┌────────┐┌─────┐│
│  │New Run ││ Alerts ││Sys  ││
│  └────────┘└────────┘└─────┘│
└─────────────────────────────┘
```

---

### 5.2 Runs List (`/runs`)

Browse and filter all training runs.

```
┌─────────────────────────────┐
│  [sticky header]            │
│  Runs                       │
│  🔍 Search runs...          │
│  [All][Running][Queued]...  │ ← horizontal scroll pills
├─────────────────────────────┤
│  [RunCard]                  │
│  [RunCard]                  │
│  [RunCard]                  │
│  ...                        │
└─────────────────────────────┘
```

**Run Card anatomy:**
```
┌─────────────────────────────────┐
│  run-name-here      [running]   │
│  configs/model.yaml             │
│  ─────────────────────────────  │
│  Step    Epoch   Loss    VLoss  │
│  1,240    3      0.312   0.341  │
│  ─────────────────────────────  │
│  Runtime: 2h 14m        Open → │
└─────────────────────────────────┘
```

---

### 5.3 Run Detail (`/runs/[id]`)

Deep dive into one run. Most-used screen during active training.

```
┌─────────────────────────────┐
│  ← Back to Runs             │
│  Run Detail                 │
│  my-experiment-v4           │
│  configs/slm_base.yaml      │
│  ─────────────────────────  │
│  [Refresh] [Sync] [Cancel]  │
│  ─────────────────────────  │
│  [Overview][Metrics][Logs]  │ ← horizontal scroll tabs
│  [Config][Job][Events]      │
├─────────────────────────────┤
│  [Tab content]              │
└─────────────────────────────┘
```

**Overview tab:**
```
┌──────────┬──────────┬────────┐
│  Step    │  Epoch   │ T.Loss │
│  1,240   │    3     │ 0.312  │
├──────────┼──────────┼────────┤
│  V.Loss  │ Runtime  │   LR   │
│  0.341   │ 2h 14m   │ 3e-4   │
└──────────┴──────────┴────────┘
+ metadata (config path, commit, W&B ref)
```

**Metrics tab:** Stacked line charts (one per metric)
```
┌─────────────────────────────┐
│  Training Loss              │
│  [LineChart 224px tall]     │
├─────────────────────────────┤
│  Validation Loss            │
│  [LineChart 224px tall]     │
├─────────────────────────────┤
│  Learning Rate              │
│  [LineChart 224px tall]     │
└─────────────────────────────┘
```

**Events tab (timeline):**
```
● status_changed   running → completed   2h ago
● metric_synced    Step 1240 synced      2h ago
● job_queued       Submitted to SLURM    3h ago
```

---

### 5.4 Config Builder (`/config-builder`)

Form to design and generate a neural network YAML config.

Sections (stacked):
- Experiment (name, tags)
- Model (architecture dropdowns: attention type, norm, MLP)
- Dimensions (vocab size, seq len, d_model, layers, heads)
- Training (batch size, steps, LR, optimizer, scheduler)
- Data (dataset source, max samples)
- Tokenizer

Actions at bottom:
```
[Generate Preview]
[Save Config]
[Save & Launch Run]
```

---

### 5.5 Alerts (`/alerts`)

All notifications in reverse-chronological order.

**Alert Card:**
```
┌──────────────────────────────────────┐
│  🔴  Run failed: my-exp-v3      2h ago│
│      OOM on node gpu-04               │
│      ● unread                         │
└──────────────────────────────────────┘
```

Icons by type: `ℹ info` · `⚠ warning` · `✖ error` · `✔ success`

---

### 5.6 System Health (`/system`)

Live status of all backend connections.

```
┌─────────────────────────────┐
│  Backend API      [healthy] │
│  M3 Cluster    [connected]  │
│  SLURM           [healthy]  │
│  Database        [healthy]  │
│  W&B            [connected] │
│  ─────────────────────────  │
│  Background Worker          │
│  Enabled: Yes               │
│  Running: Yes               │
│  Interval: 60s              │
│  Last cycle: 3 runs         │
│  ─────────────────────────  │
│  Recent Activity            │
│  Runs tracked: 17           │
│  Active: 2                  │
└─────────────────────────────┘
```

---

## 6. Component Library

### Status Badge
```
╭──────────────╮
│  ● running   │   rounded-full, 12px, medium weight
╰──────────────╯
```
Colors: see Section 1 Status Colors.

### Metric Card (small)
```
┌──────────┐
│  Step    │  label: 12px, zinc-500
│  1,240   │  value: 20px, semibold, white
└──────────┘
```

### Line Chart
- Background: card surface
- Grid lines: `#27272a` dashed
- Axes: `#71717a`, 12px
- Line: `#ffffff`, 2px, no dots
- Tooltip: dark card, `#27272a` border, 12px radius
- Height: 224px

### Filter / Tab Pill
```
Active:   ╭───────────╮  white bg, black text
          │  Running  │
          ╰───────────╯

Inactive: ╭───────────╮  zinc-900 bg, zinc-300 text
          │  Queued   │
          ╰───────────╯
```

### Buttons
| Type | Background | Text | Border |
|---|---|---|---|
| Primary | `#ffffff` | `#000000` | — |
| Secondary | `#18181b` | `#e4e4e7` | `#3f3f46` |
| Danger | `#ef4444` @ 10% | `#fca5a5` | `#ef4444` @ 20% |

### Form Input
- Background: `#000000`
- Border: `#27272a`, radius 12px
- Text: `#ffffff`, 14px
- Label: `#d4d4d8`, 14px
- Focus border: `#3f3f46`

### Log Panel
- Background: `#000000`
- Font: monospace, 12px, `#d4d4d8`
- Max height: 384px, scrollable
- Border: `#27272a`, radius 12px

---

## 7. Icon Set (Lucide React)

| Context | Icon |
|---|---|
| Home | `Home` |
| Runs | `FolderKanban` |
| Alerts | `Bell` |
| System | `Server` |
| Refresh | `RefreshCw` |
| Cancel | `Square` |
| Back | `ArrowLeft` |
| Open/Next | `ChevronRight` |
| Search | `Search` |
| Filter | `Filter` |
| New | `Plus` |
| Info alert | `Info` |
| Warning alert | `TriangleAlert` |
| Error alert | `AlertCircle` |
| Success alert | `CheckCircle2` |

Icon sizes: **16px** (nav, inline), **20px** (actions)

---

## 8. Key UX Patterns to Preserve

- **Always dark.** No light mode.
- **Bottom nav** is the primary navigation. Never a hamburger or top nav.
- **Live data** — runs and metrics auto-refresh every 10–15 s. The UI should feel "alive."
- **Status is the most important visual signal.** Color-coded badges appear on every run, every system item, every alert.
- **Runs list is the most-used screen** after dashboard. Filtering and glanceability are critical.
- **Metrics charts** are the core of the run detail screen — they need to be readable at a glance.
- **Config builder** is a power-user screen — density is acceptable here.
- **The researcher is alone** — no collaboration features, no avatars, no teams UI needed.
