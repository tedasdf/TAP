import { apiRequest } from "@/lib/api/client";

export type GenerateSlmConfigRequest = {
  experiment_name: string;
  model_name?: string;
  vocab_size?: number;
  seq_len: number;
  d_model: number;
  n_layers: number;
  n_heads: number;
  batch_size: number;
  max_steps: number;
  learning_rate: number;
  dataset_source: "fineweb_edu" | "local_jsonl" | "synthetic";
  attention_type?: string;
  normalization?: string;
  mlp_type?: string;
  optimizer?: string;
  scheduler?: string;
  tokenizer?: string;
};

export type GenerateSlmConfigResponse = {
  config: Record<string, unknown>;
  yaml: string;
};

export type SaveSlmConfigResponse = {
  config: Record<string, unknown>;
  yaml: string;
  saved_path: string;
  config_path: string;
};

export function generateSlmConfig(payload: GenerateSlmConfigRequest) {
  return apiRequest<GenerateSlmConfigResponse>("/configs/generate/slm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveSlmConfig(payload: GenerateSlmConfigRequest) {
  return apiRequest<SaveSlmConfigResponse>("/configs/save/slm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
