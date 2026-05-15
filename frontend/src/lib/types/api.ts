export type ApiRun = {
  run_id: string;
  name: string;
  status: "created" | "running" | "queued" | "failed" | "completed" | "cancelled" | "unknown";
  git_commit?: string | null;
  config_path: string;
  config_overrides?: Record<string, unknown> | null;
  wandb_config_ref?: string | null;
  slurm_job_id?: string | null;
  wandb_run_id?: string | null;
  created_at: string;
  error_message?: string | null;

  // optional summary fields if backend includes them
  current_step?: number | null;
  current_epoch?: number | null;
  training_loss?: number | null;
  validation_loss?: number | null;
  runtime?: number | string | null;
  learning_rate?: number | null;
  latest_metric_timestamp?: string | null;
  config_snapshot?: Record<string, unknown> | null;
};

export type ApiSystemStatus = {
  backend?: string;
  database?: string;
  timestamp?: string;
  database_error?: string;

  service?: string;
  status?: string;
  checks?: {
    database?: string;
    ssh?: string;
    wandb?: string;
  };

  run_count?: number;
  active_run_count?: number;
  notification_count?: number;

  m3?: string;
  slurm?: string;
  wandb?: string;
  last_sync?: string | null;
  last_job_launch?: string | null;

  background_worker?: ApiBackgroundWorkerStatus;
};

export type ApiMetricPoint = {
  run_id: string;
  step?: number | null;
  train_loss?: number | null;
  training_loss?: number | null;
  val_loss?: number | null;
  validation_loss?: number | null;
  learning_rate?: number | null;
  runtime_seconds?: number | null;
  runtime?: string | number | null;
  tokens_seen?: number | null;
  samples_seen?: number | null;
  tokens_per_second?: number | null;
  created_at: string;
  source?: string | null;
};

export type ApiRunMetrics = {
  current_step?: number | null;
  current_epoch?: number | null;
  training_loss?: number | null;
  validation_loss?: number | null;
  runtime?: number | string | null;
  learning_rate?: number | null;
  latest_metric_timestamp?: string | null;
};

export type CreateRunPayload = {
  name: string;
  git_commit?: string;
  config_path: string;
  config_overrides?: Record<string, string>;
  wandb_config_ref?: string;
  wandb_run_id?: string;
  launch_now?: boolean;
};

export type ApiNotification = {
  notification_id: string;
  event_type: string;
  severity: string;
  title: string;
  message: string;
  timestamp: string;
  read_state: boolean | number;
  run_id?: string | null;
  job_id?: string | null;
};

export type ApiRunLogFile = {
  path: string | null;
  exists: boolean;
  content: string;
  error: string | null;
};

export type ApiRunLogs = {
  run_id: string;
  job_id: string | null;
  stdout: ApiRunLogFile;
  stderr: ApiRunLogFile;
};

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

export type ApiBackgroundWorkerStatus = {
  enabled: boolean;
  running: boolean;
  interval_seconds: number;
  last_cycle_started_at?: string | null;
  last_cycle_finished_at?: string | null;
  last_cycle_run_count: number;
  last_cycle_error_count: number;
  last_error?: string | null;
};