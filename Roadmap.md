# TAP Roadmap

## Product Vision

TAP is a single-user research control panel for configuring, launching, tracking, comparing, and understanding machine learning training experiments.

The long-term goal is to let a user:

- track Slurm/W&B training runs
- preserve exact configs and reproducibility metadata
- monitor training metrics
- receive useful alerts
- generate valid model configs
- compare experiments
- run sweeps and ablations
- track checkpoints and evaluations
- eventually control experiments from a phone/laptop browser

TAP should first become excellent for the current SLM training workflow before expanding into a general neural network research platform.

---

## Roadmap Philosophy

There are two layers of planning:

### Core Product Path

This is what TAP should become first:

```text
monitoring
→ reproducibility
→ metrics
→ notifications
→ automation
→ config generation
→ component registry
→ experiment comparison
→ sweeps
→ artifacts/evaluation
```

### Dream Product Features

These are valid long-term goals, but they should not drive the early milestones:

```text
full production deployment
beautiful analytics dashboard
complex notification rules
support for every neural network type
drag-and-drop neural network builder
advanced experiment automation
```

The rule is:

> Build TAP first for the current SLM training workflow, then generalise later.

---

## Current Status

### M1 — Reliable Run Tracking

TAP can create/register runs and track real Slurm/W&B training jobs.

M1 answers:

> What is my run doing right now?

Core capabilities:

- run creation/registration
- Slurm job ID tracking
- optional W&B run ID tracking
- status refresh
- Run Detail status display
- run lifecycle tracking
- status transitions stored in database

Status:

```text
Implemented / needs final verification if not already tested end-to-end
```

Final verification checklist:

- [ ] successful Slurm job: queued → running → completed
- [ ] failed Slurm job: queued/running → failed
- [ ] frontend shows updated status
- [ ] status transitions are stored in run_events

---

### M2 — Config Visibility and Reproducibility

TAP stores and displays the metadata needed to understand what produced each run.

M2 answers:

> What exact config/code/data produced this run?

Core capabilities:

- config path
- config snapshot
- git commit tracking
- W&B metadata/link
- Run Detail reproducibility section
- launch/config metadata visibility

Status:

```text
Implemented / needs final verification if not already tested
```

Final verification checklist:

- [ ] Run Detail shows config used
- [ ] config snapshot is stored
- [ ] git commit is actual SHA, not literal HEAD
- [ ] W&B run ID/link is visible when available
- [ ] missing metadata does not crash frontend

---

# Core Milestone Path

## M3 — Metrics and Training Dashboard

### Goal

Make TAP useful for understanding training progress.

M3 answers:

> Is the model actually training well?

### Core Features

- latest training metrics
- metric history
- W&B metric sync
- train loss
- validation loss
- learning rate
- current step
- runtime
- tokens seen
- tokens per second
- simple real charts
- metric sync status
- no fake/generated chart data

### Done When

A user can open a run and understand how training is progressing using real metrics, not just job status.

---

## M4 — Basic Notifications and Alerts

### Goal

Notify the user when important things happen.

M4 answers:

> What important thing happened, and do I need to act?

### Core Features

- run started notification
- run completed notification
- run failed notification
- run cancelled notification
- stuck queued notification
- W&B sync failed notification
- Slurm unavailable notification
- in-app Alerts page
- read/unread notifications
- duplicate alert prevention

### Done When

TAP can notify the user about important run lifecycle changes and system issues without being noisy.

---

## M5 — Background Worker and Automation

### Goal

Make TAP keep itself updated when no page is open.

M5 answers:

> Can TAP update itself without me watching?

### Core Features

- background refresh loop
- active run refresh
- terminal run skipping
- scheduled Slurm sync
- scheduled W&B sync
- worker health status
- refresh timestamps
- refresh error tracking
- stuck-run checks
- manual refresh-all-active action

### Done When

TAP can keep active runs updated in the background and surface worker health clearly.

---

## M6 — Model Config Builder

### Goal

Generate valid SLM training configs from the UI.

M6 answers:

> Can TAP create a valid training config for me?

### Core Features

- model config form
- training config form
- dataset/tokenizer config form
- YAML generation
- config validation
- safe presets
- YAML preview
- save generated config
- create run from generated config

### Scope

M6 should only support:

```text
SLM decoder-only transformer configs
```

Not every neural network type yet.

### Done When

A user can open TAP, enter supported SLM settings, generate a valid YAML config, save it, and create a trackable run from that config.

---

## M7 — Component Registry

### Goal

Make TAP understand which model/training components are supported and valid.

M7 answers:

> What components can TAP safely mix together?

### Core Features

- attention registry
- normalization registry
- MLP registry
- positional encoding registry
- optimizer registry
- scheduler registry
- dataset registry
- tokenizer registry
- compatibility rules
- validation rules
- registry-backed config builder UI

### Example Components

Attention:

```text
full
GQA
sliding_window
XSA
MLA
```

Normalization:

```text
LayerNorm
RMSNorm
```

MLP:

```text
standard MLP
SwiGLU
GeGLU
```

### Done When

TAP can list supported components, validate combinations, and use the registry to drive the Config Builder UI.

---

## M8 — Experiment Templates

### Goal

Make common experiments easy to launch.

M8 answers:

> Can I start a common experiment quickly and consistently?

### Core Features

- smoke test template
- baseline SLM template
- GQA ablation template
- sliding window attention template
- XSA experiment template
- scaling-law template
- tokenizer comparison template
- dataset comparison template

### Done When

A user can start common experiments without manually filling every field.

---

## M9 — Experiment Comparison

### Goal

Help the user understand which experiment performed better and why.

M9 answers:

> Which run was better, and what changed?

### Core Features

- compare two or more runs
- compare configs
- compare metrics
- compare final validation loss
- compare runtime
- compare tokens trained
- compare architecture differences
- highlight changed fields
- group related runs
- add notes/conclusions

### Done When

TAP can help answer which experiment performed better and what changed between runs.

---

## M10 — Sweep and Ablation Generator

### Goal

Generate and launch groups of related experiments.

M10 answers:

> Can TAP help me run systematic experiments?

### Core Features

- learning rate sweep
- batch size sweep
- attention variant sweep
- model size sweep
- dataset size sweep
- tokenizer sweep
- scaling-law sweep
- experiment group creation
- group-level comparison dashboard

### Example

Base config:

```yaml
d_model: 512
num_layers: 8
learning_rate: 3e-4
```

Sweep:

```yaml
attention_type:
  - full
  - gqa
  - sliding_window
  - xsa
```

TAP generates:

- multiple configs
- multiple Slurm jobs
- one experiment group
- one comparison view

### Done When

TAP can launch and track controlled experiment groups.

---

## M11 — Artifact and Checkpoint Tracking

### Goal

Track what each run produces.

M11 answers:

> What did this run create?

### Core Features

- latest checkpoint path
- best checkpoint path
- checkpoint list
- tokenizer artifact reference
- config artifact reference
- log artifact reference
- DVC/S3 artifact reference
- artifact size
- artifact status

### Done When

TAP knows not only what ran, but what artifacts the run produced.

---

## M12 — Evaluation Tracking

### Goal

Track evaluation results after training.

M12 answers:

> How good was the trained model after evaluation?

### Core Features

- launch evaluation job
- track evaluation status
- store evaluation metrics
- compare evaluation results
- generate evaluation reports
- link evaluation result to training run

### Example Metrics

- perplexity
- validation loss
- benchmark accuracy
- inference speed
- memory usage
- custom generation tests

### Done When

TAP can track both training and evaluation in one place.

---

# Version Roadmap

## TAP v0.1 — Monitoring MVP

Focus:

- reliable run tracking
- Slurm/W&B IDs
- status refresh
- Run Detail page
- config snapshot
- basic system health

Goal:

> TAP can track real training runs correctly.

---

## TAP v0.2 — Reproducible Experiment Dashboard

Focus:

- config viewer
- git commit tracking
- run events
- basic metrics
- better Run Detail
- basic notifications
- background worker

Goal:

> TAP can tell me what happened and what produced this run.

---

## TAP v0.3 — Model Config Builder

Focus:

- model config form
- training config form
- dataset/tokenizer form
- YAML generation
- config validation
- launch from generated config

Goal:

> TAP can create a valid SLM training config from the UI.

---

## TAP v0.4 — Component Registry and Templates

Focus:

- attention options
- norm options
- MLP options
- optimizer/scheduler options
- valid component combinations
- experiment templates

Goal:

> TAP knows which supported components can be safely mixed together.

---

## TAP v0.5 — Experiment Comparison

Focus:

- compare runs
- compare configs
- compare metrics
- group related runs
- tag experiments
- write notes/conclusions

Goal:

> TAP helps identify which experiment was better and why.

---

## TAP v0.6 — Sweeps and Ablations

Focus:

- generate multiple configs
- launch multiple jobs
- track experiment groups
- compare sweep results

Goal:

> TAP helps run systematic experiment groups.

---

## TAP v1.0 — Research Control Platform

Focus:

- remote launch
- monitoring
- config generation
- component registry
- experiment groups
- metrics
- notifications
- artifact tracking
- evaluation tracking
- mobile-friendly control panel
- production-ready workflow

Goal:

> TAP supports a full ML research workflow from idea to experiment to result comparison.

---

## TAP v2.0 — General Neural Network Research Platform

Focus:

- support more model families
- full production deployment
- beautiful analytics dashboard
- complex notification rules
- drag-and-drop neural network builder
- advanced experiment automation

Goal:

> TAP becomes a broader neural network research platform beyond the initial SLM workflow.

---

# Dream Product Features

These are valid long-term goals, but they should come after the core workflow is useful.

## Full Production Deployment

Belongs around:

```text
v1.0+
```

Before that, use:

- Docker
- README
- local server
- SSH tunnel
- private network access

---

## Beautiful Analytics Dashboard

Belongs after:

```text
real metrics
metric history
run comparison
```

Do not build beautiful charts before the data is real.

---

## Complex Notification Rules

Belongs after:

```text
basic notifications
background worker
stuck-run detection
metric sync status
```

Start simple:

- run started
- run completed
- run failed
- stuck queued
- W&B sync failed

---

## Support for Every Neural Network Type

Belongs around:

```text
v2.0+
```

Start with:

```text
SLM decoder-only transformer
```

Expand later into:

- CNNs
- diffusion models
- RL agents
- vision transformers
- multimodal models

---

## Drag-and-Drop Neural Network Builder

Belongs far later.

Before this, TAP needs:

- config builder
- component registry
- validation rules
- templates
- sweeps
- run comparison

---

## Advanced Experiment Automation

Belongs after:

- sweeps
- evaluation tracking
- artifact tracking
- run comparison

Advanced automation should not come before TAP can reliably store, compare, and evaluate experiments.

---

# Recommended Build Order From Current State

Since M1 and M2 are already implemented or near completion, the next build order is:

```text
1. Verify M1 and M2 are fully closed
2. M3 — Metrics and Training Dashboard
3. M4 — Basic Notifications and Alerts
4. M5 — Background Worker and Automation
5. M6 — Model Config Builder
6. M7 — Component Registry
7. M8 — Experiment Templates
8. M9 — Experiment Comparison
9. M10 — Sweep and Ablation Generator
10. M11 — Artifact / Checkpoint Tracking
11. M12 — Evaluation Tracking
```

---

# Current Next Step

The next core milestone should be:

```text
M3 — Metrics and Training Dashboard
```

Reason:

After TAP tracks runs and stores configs, the next useful question is:

> Is the training actually going well?

M3 should focus on:

- real metric history
- latest train loss
- latest validation loss
- learning rate
- current step
- runtime
- tokens seen
- W&B sync
- simple charts
- no fake chart data

---

# Scope Control Rule

Do not jump from:

```text
reliable run tracking
```

straight to:

```text
universal neural network builder
```

The correct path is:

```text
reliable tracking
→ reproducibility
→ metrics
→ notifications
→ automation
→ config generation
→ component registry
→ comparison
→ sweeps
→ artifacts/evaluation
→ broader model families
```

---

# One-Sentence Product Direction

TAP should first become an excellent research control panel for the current SLM training workflow, then gradually expand into a broader neural network experiment platform.