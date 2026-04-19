import { apiRequest } from "@/lib/api/client";

export type ApiJob = {
  job_id: string;
  run_id?: string | null;
  queue_state?: string | null;
  execution_state?: string | null;
  node_info?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  exit_status?: string | null;
  log_path?: string | null;
  error_log_path?: string | null;
};

export type ApiJobLogs = {
  logs?: string[];
  stdout?: string[];
  stderr?: string[];
};

export function getJob(jobId: string) {
  return apiRequest<ApiJob>(`/jobs/${jobId}`);
}

export function getJobLogs(jobId: string) {
  return apiRequest<ApiJobLogs>(`/jobs/${jobId}/logs`);
}