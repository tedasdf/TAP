export type ApiRunStatus =
  | "created"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "unknown";

export type ApiRun = {
  run_id: string;
  name: string;
  status: ApiRunStatus;
  git_commit?: string | null;
  config_path: string;
  config_overrides?: Record<string, unknown> | null;
  config_snapshot?: Record<string, unknown> | null;
  wandb_config_ref?: string | null;
  slurm_job_id?: string | null;
  wandb_run_id?: string | null;
  created_at: string;
  last_checked_at?: string | null;
  error_message?: string | null;
  template_id?: string | null;

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
  title?: string | null;
  message: string;
  run_id?: string | null;
  job_id?: string | null;
  timestamp: string;
  read_state: boolean | number;
};

export type ApiSystemStatus = {
  status?: string;
  backend?: string;
  m3?: string;
  slurm?: string;
  database?: string;
  wandb?: string;
  last_sync?: string | null;
  last_job_launch?: string | null;
  checks?: {
    ssh?: string;
    database?: string;
    slurm?: string;
    wandb?: string;
  };
  background_worker?: {
    enabled?: boolean;
    running?: boolean;
    interval_seconds?: number;
    last_cycle_run_count?: number;
    last_cycle_error_count?: number;
    last_cycle_finished_at?: string | null;
    last_error?: string | null;
  };
  run_count?: number;
  active_run_count?: number;
  notification_count?: number;
  timestamp?: string;
  database_error?: string | null;
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

export type ApiMetricPoint = {
  point_id: string;
  run_id: string;
  step: number;
  epoch?: number | null;
  source: string;
  metrics: Record<string, number>;
  created_at?: string | null;
};

export type CreateRunPayload = {
  name: string;
  config_path: string;
  config_overrides?: Record<string, unknown>;
  wandb_config_ref?: string | null;
  wandb_run_id?: string | null;
  submit_script?: string | null;
  launch_now?: boolean;
  launch_mode?: "slurm" | "direct";
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

export type ParamSpec =
  | { role: "fixed"; value: string | number }
  | { role: "vary"; values: (string | number)[] }
  | { role: "derive"; expr: string; from: string };

export type ApiTemplate = {
  template_id: string;
  name: string;
  description: string | null;
  params: Record<string, ParamSpec>;
  created_at: string;
  run_count: number;
};

export type ApiTemplateSummary = ApiTemplate & {
  runs: Array<{
    run_id: string;
    name: string;
    status: string;
    combo_index: number;
    created_at: string;
  }>;
};

export type CreateTemplatePayload = {
  name: string;
  description?: string | null;
  params: Record<string, ParamSpec>;
};

export type ApiTemplateRunItem = {
  run_id: string;
  name: string;
  combo_index: number;
  status: string;
  slurm_job_id: string | null;
  created_at: string;
  params: Record<string, string | number>;
  metrics: {
    training_loss: number | null;
    validation_loss: number | null;
    learning_rate: number | null;
    current_step: number | null;
    latest_metric_timestamp: string | null;
  } | null;
};

export type ApiTemplateRunsResponse = {
  template_id: string;
  template_name: string;
  runs: ApiTemplateRunItem[];
};

export type ApiRunCombo = {
  combo_index: number;
  params: Record<string, string | number>;
  derive_trace: Record<string, string>;
};

export type ApiPreviewResponse = {
  template_id: string;
  total_runs: number;
  combos: ApiRunCombo[];
};

export type ApiCompareEntry = {
  run_id: string;
  name: string;
  status: ApiRunStatus;
  git_commit: string;
  config_path: string;
  created_at: string;
  error_message: string | null;
  current_step: number | null;
  current_epoch: number | null;
  training_loss: number | null;
  validation_loss: number | null;
  best_validation_loss: number | null;
  learning_rate: number | null;
  runtime: number | null;
  config_overrides: Record<string, unknown>;
  config_snapshot: Record<string, unknown> | null;
};
 
export type ApiCompareResponse = {
  runs: ApiCompareEntry[];
  config_diff: Record<string, Record<string, unknown>>;
};


export type ApiMetricSyncStatus = {
  run_id: string;
  source: string | null;
  status: string;
  last_started_at: string | null;
  last_finished_at: string | null;
  error_message: string | null;
  points_synced: number;
};

export type RunEvent = {
  event_id: string;
  run_id: string;
  event_type: string;
  message: string;
  old_status: string | null;
  new_status: string | null;
  created_at: string;
  payload: Record<string, unknown>;
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

export type RefreshActiveRunsResponse = {
  total: number;
  refreshed: Array<{ run_id: string; status: string }>;
  failed: Array<{ run_id: string; error: string }>;
  refreshed_count: number;
  failed_count: number;
};
 