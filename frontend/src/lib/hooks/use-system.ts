"use client";

import { useQuery } from "@tanstack/react-query";
import { getSystemStatus } from "@/lib/api/system";

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system-status"],
    queryFn: getSystemStatus,
    refetchInterval: 20000,
  });
}