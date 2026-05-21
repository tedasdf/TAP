"use client";

import { useQuery } from "@tanstack/react-query";
import { getSlmRegistry } from "@/lib/api/registry";

export function useSlmRegistry() {
  return useQuery({
    queryKey: ["registry", "slm"],
    queryFn: getSlmRegistry,
  });
}