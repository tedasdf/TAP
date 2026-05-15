export type RunStatus = "running" | "queued" | "failed" | "completed" | "cancelled";

export type HealthState = "healthy" | "connected" | "degraded" | "disconnected" | "unknown";

export type RunCardView = {
  id: string;
  name: string;
  status: RunStatus;
  configPath: string;
  currentStep?: number;
  currentEpoch?: number;
  trainingLoss?: number;
  validationLoss?: number;
  runtime?: string;
  errorMessage?: string | null;
  slurmJobId?: string | null;
};

export type AlertView = {
  id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
};

export type StatusStripView = {
  backend: HealthState;
  m3: HealthState;
  slurm: HealthState;
  wandb: HealthState;
};

export type SummaryCounts = {
  running: number;
  queued: number;
  failed: number;
  completed: number;
};

export type AttentionItem = {
  id: string;
  title: string;
  message: string;
  severity: "warning" | "error";
  runId?: string;
};

export type NotificationView = {
  id: string;
  title: string;
  message: string;
  severity: string;
  isRead: boolean;
  createdAtLabel: string;
  runId?: string;
};