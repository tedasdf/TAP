"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelRun, createRun, getRun, getRunEvents, getRunMetricHistory, getRunMetrics, getRuns, refreshRun, syncWandb } from "@/lib/api/runs";
import { CreateRunPayload } from "@/lib/types/api";

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

export function useRunMetricHistory(runId: string) {
  return useQuery({
    queryKey: ["runs", runId, "metrics", "history"],
    queryFn: () => getRunMetricHistory(runId),
    enabled: !!runId,
    refetchInterval: 15000,
  });
}

export function useRunEvents(runId: string) {
  return useQuery({
    queryKey: ["run-events", runId],
    queryFn: () => getRunEvents(runId),
    enabled: Boolean(runId),
    refetchInterval: 10_000,
  });
}

export function useRefreshRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => refreshRun(runId),
    onSuccess: (_data, runId) => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["runs", runId] });
      queryClient.invalidateQueries({ queryKey: ["runs", runId, "metrics"] });
      queryClient.invalidateQueries({ queryKey: ["runs", runId, "metrics", "history"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
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
    onSuccess: (_data, runId) => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["runs", runId] });
      queryClient.invalidateQueries({ queryKey: ["runs", runId, "metrics"] });
      queryClient.invalidateQueries({ queryKey: ["runs", runId, "metrics", "history"] });
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