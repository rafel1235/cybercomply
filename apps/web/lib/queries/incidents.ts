"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export interface IncidentNotification {
  id: string;
  phase: string;
  sent_at: string;
  recipient: string;
  content: string | null;
}

export interface IncidentDeadline {
  phase: string;
  due_at: string;
  sent: boolean;
  sent_at: string | null;
  overdue: boolean;
}

export interface Incident {
  id: string;
  reference_code: string;
  incident_type: string;
  status: "aperto" | "in_gestione" | "chiuso";
  opened_at: string;
  closed_at: string | null;
  data: Record<string, unknown>;
  notifications: IncidentNotification[];
  deadlines: IncidentDeadline[];
}

export function useIncidents(statusFilter?: string) {
  const api = useApi();
  return useQuery<Incident[]>({
    queryKey: ["incidents", statusFilter ?? "all"],
    queryFn: () =>
      api.get(statusFilter ? `/incidents?status_filter=${statusFilter}` : "/incidents"),
  });
}

export function useIncident(id: string) {
  const api = useApi();
  return useQuery<Incident>({
    queryKey: ["incidents", "detail", id],
    queryFn: () => api.get(`/incidents/${id}`),
    enabled: Boolean(id),
  });
}

export function useCreateIncident() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { incident_type: string; data?: Record<string, unknown> }) =>
      api.post("/incidents", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useCloseIncident() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/incidents/${id}/close`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useRecordNotification() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      incidentId,
      phase,
      recipient,
      content,
    }: {
      incidentId: string;
      phase: string;
      recipient: string;
      content?: string;
    }) => api.post(`/incidents/${incidentId}/notifications`, { phase, recipient, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
