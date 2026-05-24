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