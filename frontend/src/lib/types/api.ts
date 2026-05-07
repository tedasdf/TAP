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
};

export type ApiNotification = {
  notification_id: string;
  event_type: string;
  message: string;
  run_id?: string | null;
  job_id?: string | null;
  timestamp: string;
  read_state: boolean;
};

export type ApiSystemStatus = {
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
  backend?: string;
  m3?: string;
  slurm?: string;
  database?: string;
  wandb?: string;
  last_sync?: string | null;
  last_job_launch?: string | null;
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


export type ApiMetricHistoryPoint = {
  metric_id: string;
  run_id: string;
  step?: number | null;
  epoch?: number | null;
  train_loss?: number | null;
  val_loss?: number | null;
  learning_rate?: number | null;
  runtime_seconds?: number | null;
  tokens_seen?: number | null;
  samples_seen?: number | null;
  tokens_per_second?: number | null;
  gpu_memory_used?: number | null;
  gpu_utilization?: number | null;
  source: string;
  created_at: string;
};

export type CreateRunPayload = {
  name: string;
  git_commit: string;
  config_path: string;
  config_overrides?: Record<string, string>;
  wandb_config_ref?: string;
  wandb_run_id?: string;
  launch_now?: boolean;
};