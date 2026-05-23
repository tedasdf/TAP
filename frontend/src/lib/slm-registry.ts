export type RegistryField<T extends string | number> = { options: T[] };

export type SlmRegistry = {
  model: {
    attention_type: RegistryField<string>;
    normalization: RegistryField<string>;
    mlp_type: RegistryField<string>;
    d_model: RegistryField<number>;
    n_heads: RegistryField<number>;
    n_layers: RegistryField<number>;
    seq_len: RegistryField<number>;
  };
  training: {
    learning_rate: RegistryField<number>;
    batch_size: RegistryField<number>;
    max_steps: RegistryField<number>;
    scheduler: RegistryField<string>;
    optimizer: RegistryField<string>;
  };
  data: {
    source_type: RegistryField<string>;
    dataset_name: RegistryField<string>;
    dataset_config_name: RegistryField<string>;
  };
};

export type ParamValue = string | number;
export type ParamMap = Record<string, ParamValue>;

export const slmRegistry: SlmRegistry = {
  model: {
    attention_type: { options: ["baseline", "gqa", "mha"] },
    normalization: { options: ["rmsnorm", "layernorm", "none"] },
    mlp_type: { options: ["gelu", "silu", "relu"] },
    d_model: { options: [128, 256, 512, 1024] },
    n_heads: { options: [2, 4, 8, 16] },
    n_layers: { options: [2, 4, 6, 8, 12] },
    seq_len: { options: [128, 256, 512, 1024, 2048] },
  },
  training: {
    learning_rate: { options: [0.001, 0.0003, 0.0001, 0.00003] },
    batch_size: { options: [4, 8, 16, 32] },
    max_steps: { options: [100, 500, 1000, 5000, 10000] },
    scheduler: { options: ["cosine", "linear", "constant"] },
    optimizer: { options: ["adamw", "adam"] },
  },
  data: {
    source_type: { options: ["huggingface", "local"] },
    dataset_name: { options: ["HuggingFaceFW/fineweb-edu", "openwebtext", "wikitext-103"] },
    dataset_config_name: { options: ["sample-10BT", "sample-100BT", "default"] },
  },
};

export const defaultParams: ParamMap = {
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
  "data.dataset_config_name": "sample-10BT",
};

export const DEFAULT_PARAMS = defaultParams;

export function formatValue(v: ParamValue): string {
  if (typeof v === "string") return v;
  if (Number.isInteger(v) && (v as number) >= 1000 && (v as number) % 1000 === 0) return `${(v as number) / 1000}k`;
  if (Number.isInteger(v)) return String(v);
  if (Math.abs(v as number) < 0.01) return (v as number).toExponential().replace("e-0", "e-");
  return String(v);
}

function yamlScalar(v: ParamValue): string {
  if (typeof v === "string") return v;
  if (Number.isInteger(v)) return String(v);
  if (Math.abs(v as number) < 0.01) return (v as number).toExponential().replace("e-0", "e-");
  return String(v);
}

export function generateYaml(name: string, params: ParamMap): string {
  const groups: Record<string, Record<string, ParamValue>> = {};
  for (const [key, value] of Object.entries(params)) {
    const dot = key.indexOf(".");
    const section = key.slice(0, dot);
    const leaf = key.slice(dot + 1);
    if (!groups[section]) groups[section] = {};
    groups[section][leaf] = value;
  }
  const lines: string[] = [];
  lines.push("experiment:");
  lines.push(`  name: ${name || "untitled"}`);
  lines.push("  family: slm");
  for (const section of ["model", "training", "data"]) {
    if (!groups[section]) continue;
    lines.push(`${section}:`);
    for (const [leaf, value] of Object.entries(groups[section])) {
      lines.push(`  ${leaf}: ${yamlScalar(value)}`);
    }
  }
  return lines.join("\n") + "\n";
}

export function generatedPath(name: string): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const ts = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  const safe = (name || "untitled").trim().replace(/[^a-zA-Z0-9_-]+/g, "-");
  return `generated_configs/slm/${safe}-${ts}.yaml`;
}
