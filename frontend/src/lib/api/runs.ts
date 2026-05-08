import { apiRequest } from "@/lib/api/client";
import { ApiMetricPoint, ApiRun, ApiRunMetrics, CreateRunPayload } from "@/lib/types/api";

export function getRuns() {
  return apiRequest<ApiRun[]>("/runs");
}

export function getRun(runId: string) {
  return apiRequest<ApiRun>(`/runs/${runId}`);
}

export function getRunMetrics(runId: string) {
  return apiRequest<ApiRunMetrics>(`/runs/${runId}/metrics`);
}

export function getRunMetricHistory(runId: string) {
  return apiRequest<ApiMetricPoint[]>(`/runs/${runId}/metrics/history`);
}

export function refreshRun(runId: string) {
  return apiRequest(`/runs/${runId}/refresh`, {
    method: "POST",
  });
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

export type RunEvent = {
  event_id: string;
  run_id: string;
  event_type: string;
  message: string;
  old_status?: string | null;
  new_status?: string | null;
  created_at: string;
  payload?: Record<string, unknown>;
};

export async function getRunEvents(runId: string): Promise<RunEvent[]> {
  return apiRequest<RunEvent[]>(`/runs/${runId}/events`);
}