import { apiRequest } from "./client";
import type {
  ApiPreviewResponse,
  ApiTemplate,
  ApiTemplateSummary,
  ApiTemplateRunsResponse,
  CreateTemplatePayload,
} from "@/lib/types/api";

export async function getTemplates(): Promise<ApiTemplate[]> {
  const res = await apiRequest<{ templates: ApiTemplate[] }>("/templates");
  return res.templates;
}

export async function getTemplate(templateId: string): Promise<ApiTemplateSummary> {
  return apiRequest<ApiTemplateSummary>(`/templates/${templateId}`);
}

export async function createTemplate(payload: CreateTemplatePayload): Promise<ApiTemplate> {
  return apiRequest<ApiTemplate>("/templates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function launchTemplate(
  templateId: string,
  payload: { dry_run?: boolean; git_commit?: string; max_steps?: number } = {},
): Promise<{ template_id: string; total: number; launched: number; failed: number }> {
  return apiRequest(`/templates/${templateId}/launch`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTemplateRuns(templateId: string): Promise<ApiTemplateRunsResponse> {
  return apiRequest<ApiTemplateRunsResponse>(`/templates/${templateId}/runs`);
}

export async function getTemplatePreview(templateId: string): Promise<ApiPreviewResponse> {
  return apiRequest<ApiPreviewResponse>(`/templates/${templateId}/preview`);
}
