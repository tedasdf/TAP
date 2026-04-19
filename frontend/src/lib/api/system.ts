import { apiRequest } from "@/lib/api/client";
import { ApiSystemStatus } from "@/lib/types/api";

export function getSystemStatus() {
  return apiRequest<ApiSystemStatus>("/system/status");
}

export function getHealth() {
  return apiRequest("/health");
}