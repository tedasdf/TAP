"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTemplate,
  getTemplate,
  getTemplatePreview,
  getTemplateRuns,
  getTemplates,
  launchTemplate,
} from "@/lib/api/templates";
import type { ApiTemplate, CreateTemplatePayload } from "@/lib/types/api";

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: getTemplates,
    refetchInterval: 30_000,
  });
}

export function useTemplate(templateId: string) {
  return useQuery({
    queryKey: ["templates", templateId],
    queryFn: () => getTemplate(templateId) as Promise<ApiTemplate>,
    enabled: !!templateId,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateTemplatePayload) => createTemplate(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
  });
}

export function useTemplateRuns(templateId: string) {
  return useQuery({
    queryKey: ["templates", templateId, "runs"],
    queryFn: () => getTemplateRuns(templateId),
    enabled: !!templateId,
    refetchInterval: 15_000,
  });
}

export function useTemplatePreview(templateId: string) {
  return useQuery({
    queryKey: ["templates", templateId, "preview"],
    queryFn: () => getTemplatePreview(templateId),
    enabled: !!templateId,
  });
}

export function useLaunchTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ templateId, dryRun = false }: { templateId: string; dryRun?: boolean }) =>
      launchTemplate(templateId, { dry_run: dryRun }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}
