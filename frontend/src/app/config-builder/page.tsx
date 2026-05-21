"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { generateSlmConfig, saveSlmConfig } from "@/lib/api/configs";
import { createRun } from "@/lib/api/runs";
import { useSlmRegistry } from "@/lib/hooks/use-registry";

type DatasetSource = "fineweb_edu" | "local_jsonl" | "synthetic";

type SelectOption = {
  id: string;
  label: string;
  description?: string;
};

export default function ConfigBuilderPage() {
  const registryQuery = useSlmRegistry();

  const datasetOptions = registryQuery.data?.dataset ?? [
    { id: "fineweb_edu", label: "FineWeb-Edu" },
    { id: "local_jsonl", label: "Local JSONL" },
    { id: "synthetic", label: "Synthetic" },
  ];

  const attentionOptions = registryQuery.data?.attention ?? [
    { id: "baseline", label: "Baseline full attention" },
  ];

  const normalizationOptions = registryQuery.data?.normalization ?? [
    { id: "rmsnorm", label: "RMSNorm" },
  ];

  const mlpOptions = registryQuery.data?.mlp ?? [
    { id: "gelu", label: "GELU MLP" },
  ];

  const optimizerOptions = registryQuery.data?.optimizer ?? [
    { id: "adamw", label: "AdamW" },
  ];

  const schedulerOptions = registryQuery.data?.scheduler ?? [
    { id: "cosine", label: "Cosine decay" },
  ];

  const tokenizerOptions = registryQuery.data?.tokenizer ?? [
    { id: "bpe", label: "BPE" },
  ];

  const [savedPath, setSavedPath] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [createdRunId, setCreatedRunId] = useState("");
  const [isCreatingRun, setIsCreatingRun] = useState(false);

  const [experimentName, setExperimentName] = useState("test-generated");
  const [modelName, setModelName] = useState("small-transformer");
  const [vocabSize, setVocabSize] = useState(50257);
  const [seqLen, setSeqLen] = useState(256);
  const [dModel, setDModel] = useState(256);
  const [nLayers, setNLayers] = useState(4);
  const [nHeads, setNHeads] = useState(4);
  const [batchSize, setBatchSize] = useState(4);
  const [maxSteps, setMaxSteps] = useState(100);
  const [learningRate, setLearningRate] = useState(0.0003);

  const [datasetSource, setDatasetSource] = useState<DatasetSource>("fineweb_edu");
  const [attentionType, setAttentionType] = useState("baseline");
  const [normalization, setNormalization] = useState("rmsnorm");
  const [mlpType, setMlpType] = useState("gelu");
  const [optimizer, setOptimizer] = useState("adamw");
  const [scheduler, setScheduler] = useState("cosine");
  const [tokenizer, setTokenizer] = useState("bpe");

  const [yamlPreview, setYamlPreview] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const configPayload = {
    experiment_name: experimentName,
    model_name: modelName,
    vocab_size: vocabSize,
    seq_len: seqLen,
    d_model: dModel,
    n_layers: nLayers,
    n_heads: nHeads,
    batch_size: batchSize,
    max_steps: maxSteps,
    learning_rate: learningRate,
    dataset_source: datasetSource,
    attention_type: attentionType,
    normalization,
    mlp_type: mlpType,
    optimizer,
    scheduler,
    tokenizer,
  };

  async function handleGenerate() {
    setIsGenerating(true);
    setError(null);
    setSavedPath("");
    setCreatedRunId("");

    try {
      const result = await generateSlmConfig(configPayload);
      setYamlPreview(result.yaml);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to generate config");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    setError(null);
    setCreatedRunId("");

    try {
      const result = await saveSlmConfig(configPayload);
      setYamlPreview(result.yaml);
      setSavedPath(result.config_path);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to save config");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateRun() {
    if (!savedPath) {
      setError("Save the config before creating a run.");
      return;
    }

    setIsCreatingRun(true);
    setError(null);

    try {
      const result = await createRun({
        name: experimentName,
        config_path: savedPath,
        launch_now: false,
      });

      setCreatedRunId(result.run_id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to create run");
    } finally {
      setIsCreatingRun(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <p className="text-sm text-zinc-500">TAP</p>
          <h1 className="mt-1 text-2xl font-bold text-white">Config Builder</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Generate a valid SLM training config and preview the YAML before saving or launching.
          </p>

          {registryQuery.isError ? (
            <p className="mt-2 text-sm text-amber-300">
              Registry could not be loaded. Using fallback component options.
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
            <h2 className="text-sm font-semibold text-white">SLM settings</h2>

            <div className="mt-4 space-y-3">
              <TextInput label="Experiment name" value={experimentName} onChange={setExperimentName} />
              <TextInput label="Model name" value={modelName} onChange={setModelName} />

              <NumberInput label="Vocab size" value={vocabSize} onChange={setVocabSize} />
              <NumberInput label="Sequence length" value={seqLen} onChange={setSeqLen} />
              <NumberInput label="d_model" value={dModel} onChange={setDModel} />
              <NumberInput label="Layers" value={nLayers} onChange={setNLayers} />
              <NumberInput label="Heads" value={nHeads} onChange={setNHeads} />
              <NumberInput label="Batch size" value={batchSize} onChange={setBatchSize} />
              <NumberInput label="Max steps" value={maxSteps} onChange={setMaxSteps} />

              <SelectInput
                label="Attention"
                value={attentionType}
                onChange={setAttentionType}
                options={attentionOptions}
              />

              <SelectInput
                label="Normalization"
                value={normalization}
                onChange={setNormalization}
                options={normalizationOptions}
              />

              <SelectInput
                label="MLP"
                value={mlpType}
                onChange={setMlpType}
                options={mlpOptions}
              />

              <SelectInput
                label="Optimizer"
                value={optimizer}
                onChange={setOptimizer}
                options={optimizerOptions}
              />

              <SelectInput
                label="Scheduler"
                value={scheduler}
                onChange={setScheduler}
                options={schedulerOptions}
              />

              <SelectInput
                label="Tokenizer"
                value={tokenizer}
                onChange={setTokenizer}
                options={tokenizerOptions}
              />

              <div>
                <label className="text-xs text-zinc-500">Learning rate</label>
                <input
                  className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white outline-none"
                  type="number"
                  step="0.00001"
                  value={learningRate}
                  onChange={(event) => setLearningRate(Number(event.target.value))}
                />
              </div>

              <SelectInput
                label="Dataset source"
                value={datasetSource}
                onChange={(value) => setDatasetSource(value as DatasetSource)}
                options={datasetOptions}
              />

              {error ? (
                <p className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
                  {error}
                </p>
              ) : null}

              <button
                className="w-full rounded-xl bg-white px-4 py-2 text-sm font-semibold text-zinc-950 disabled:opacity-60"
                onClick={handleGenerate}
                disabled={isGenerating}
              >
                {isGenerating ? "Generating..." : "Generate YAML"}
              </button>

              <button
                className="w-full rounded-xl border border-zinc-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Save Config"}
              </button>

              {savedPath ? (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-200">
                  <p className="font-semibold">Config saved</p>
                  <p className="mt-1 break-all text-xs">{savedPath}</p>
                </div>
              ) : null}

              <button
                className="w-full rounded-xl border border-emerald-500/40 px-4 py-2 text-sm font-semibold text-emerald-200 disabled:opacity-60"
                onClick={handleCreateRun}
                disabled={!savedPath || isCreatingRun}
              >
                {isCreatingRun ? "Creating run..." : "Create Run from Saved Config"}
              </button>

              {createdRunId ? (
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-3 text-sm text-blue-200">
                  <p className="font-semibold">Run created</p>
                  <p className="mt-1 break-all text-xs">{createdRunId}</p>
                </div>
              ) : null}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
            <h2 className="text-sm font-semibold text-white">YAML preview</h2>

            {yamlPreview ? (
              <pre className="mt-4 max-h-[640px] overflow-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-100">
                {yamlPreview}
              </pre>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-zinc-800 p-6 text-sm text-zinc-500">
                Generate a config to preview YAML here.
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function TextInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="text-xs text-zinc-500">{label}</label>
      <input
        className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <label className="text-xs text-zinc-500">{label}</label>
      <input
        className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white outline-none"
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

function SelectInput({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
}) {
  return (
    <div>
      <label className="text-xs text-zinc-500">{label}</label>
      <select
        className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}