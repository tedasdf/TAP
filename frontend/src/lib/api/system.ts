import { apiRequest } from "@/lib/api/client";
import type { ApiSystemStatus } from "@/lib/types/api";

export function getSystemStatus() {
  return apiRequest<ApiSystemStatus>("/system/status");
}

export function getHealth() {
  return apiRequest<ApiSystemStatus>("/health");
}