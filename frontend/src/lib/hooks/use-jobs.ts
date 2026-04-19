"use client";

import { useQuery } from "@tanstack/react-query";
import { getJob, getJobLogs } from "@/lib/api/jobs";

export function useJob(jobId?: string | null) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: 10000,
  });
}

export function useJobLogs(jobId?: string | null) {
  return useQuery({
    queryKey: ["jobs", jobId, "logs"],
    queryFn: () => getJobLogs(jobId!),
    enabled: !!jobId,
    refetchInterval: 15000,
  });
}