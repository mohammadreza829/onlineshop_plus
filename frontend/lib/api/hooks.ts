"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
export function useApi<T>(path: string, enabled = true) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: ({ signal }) => api<T>(path, { signal }),
    enabled,
  });
}
