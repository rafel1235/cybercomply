"use client";

import { useQuery } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export interface AuditLogEntry {
  id: string;
  action: string;
  entity: string | null;
  details: Record<string, unknown>;
  user_id: string | null;
  created_at: string;
}

export function useAuditLog(limit = 10) {
  const api = useApi();
  return useQuery<AuditLogEntry[]>({
    queryKey: ["audit-log", limit],
    queryFn: () => api.get(`/audit-log?limit=${limit}`),
  });
}
