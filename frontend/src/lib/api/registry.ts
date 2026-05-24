import { apiRequest } from "@/lib/api/client";

export type RegistryOption = {
  id: string;
  label: string;
  description?: string;
};

export type SlmRegistry = {
  family: string;
  model_types: RegistryOption[];
  attention: RegistryOption[];
  normalization: RegistryOption[];
  mlp: RegistryOption[];
  optimizer: RegistryOption[];
  scheduler: RegistryOption[];
  dataset: RegistryOption[];
  tokenizer: RegistryOption[];
  compatibility_rules: {
    id: string;
    message: string;
  }[];
};

export function getSlmRegistry() {
  return apiRequest<SlmRegistry>("/registry/slm");
}

export function refreshRegistry() {
  return apiRequest<SlmRegistry>("/registry/slm/refresh", { method: "POST" });
}