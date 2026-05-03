"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelRun, createRun, getRun, getRunMetrics, getRuns, syncWandb } from "@/lib/api/runs";
import { CreateRunPayload } from "@/lib/types/api";
import { refreshRun } from "@/lib/api/runs";


export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: getRuns,
    refetchInterval: 15000,
  });
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ["runs", runId],
    queryFn: () => getRun(runId),
    enabled: !!runId,
    refetchInterval: 10000,
  });
}

export function useRunMetrics(runId: string) {
  return useQuery({
    queryKey: ["runs", runId, "metrics"],
    queryFn: () => getRunMetrics(runId),
    enabled: !!runId,
    refetchInterval: 15000,
  });
}

export function useCancelRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => cancelRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

export function useSyncWandb() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => syncWandb(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateRunPayload) => createRun(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}


export function useRefreshRun() {
  return useMutation({
    mutationFn: refreshRun,
  });
}