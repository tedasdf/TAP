export type ApiRun = {
  run_id: string;
  name: string;
  status: "running" | "queued" | "failed" | "completed" | "cancelled";
  git_commit?: string | null;
  config_path: string;
  config_overrides?: string | null;
  wandb_config_ref?: string | null;
  slurm_job_id?: string | null;
  wandb_run_id?: string | null;
  created_at: string;
  last_checked_at?: string | null;
  error_message?: string | null;

  // optional summary fields if backend includes them
  current_step?: number | null;
  current_epoch?: number | null;
  training_loss?: number | null;
  validation_loss?: number | null;
  runtime?: string | null;
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
  runtime?: string | null;
  learning_rate?: number | null;
  latest_metric_timestamp?: string | null;
};

export type CreateRunPayload = {
  name: string;
  config_path: string;
  config_overrides?: string;
  wandb_config_ref?: string;
};



export type ApiRunRefreshResponse = {
  run: ApiRun;
  job: unknown | null;
  sync: {
    checked_at: string;
    message?: string;
    slurm_job_id?: string;
    status_changed?: boolean;
    old_status?: string;
    new_status?: string;
    source?: string;
  };
};