import { apiRequest } from "@/lib/api/client";
import type { ApiRunLogs, RunEvent } from "@/lib/types/api";
import { ApiMetricPoint, ApiRun, ApiRunMetrics, CreateRunPayload } from "@/lib/types/api";



export function getRunLogs(runId: string, tailLines = 300) {
  return apiRequest<ApiRunLogs>(
    `/runs/${runId}/logs?tail_lines=${tailLines}`,
  );
}

export function getRuns() {
  return apiRequest<ApiRun[]>("/runs");
}

export function getRun(runId: string) {
  return apiRequest<ApiRun>(`/runs/${runId}`);
}

export function getRunMetrics(runId: string) {
  return apiRequest<ApiRunMetrics>(`/runs/${runId}/metrics`);
}

export async function getRunMetricHistory(runId: string): Promise<ApiMetricPoint[]> {
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

export async function getRunEvents(runId: string): Promise<RunEvent[]> {
  return apiRequest<RunEvent[]>(`/runs/${runId}/events`);
}
