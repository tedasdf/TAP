import { apiRequest } from "@/lib/api/client";
import { ApiRun, ApiRunMetrics, ApiRunRefreshResponse, CreateRunPayload } from "@/lib/types/api";

export function getRuns() {
  return apiRequest<ApiRun[]>("/runs");
}

export function getRun(runId: string) {
  return apiRequest<ApiRun>(`/runs/${runId}`);
}

export function getRunMetrics(runId: string) {
  return apiRequest<ApiRunMetrics>(`/runs/${runId}/metrics`);
}

export function syncWandb(runId: string) {
  return apiRequest(`/runs/${runId}/sync-wandb`, {
    method: "POST",
  });
}

export function cancelRun(runId: string) {
  return apiRequest(`/runs/${runId}/cancel`, {
    method: "POST",
  });
}

export function createRun(payload: CreateRunPayload) {
  return apiRequest<ApiRun>("/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function refreshRun(runId: string): Promise<ApiRunRefreshResponse> {
  return apiRequest<ApiRunRefreshResponse>(`/runs/${runId}/refresh`, {
    method: "POST",
  });
}

export function deleteRun(runId: string) {
  return apiRequest<void>(`/runs/${runId}`, { method: "DELETE" });
}