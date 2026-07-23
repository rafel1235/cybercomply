"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export interface ComplianceMeasure {
  id: string;
  measure_id: string;
  label: string;
  normative_reference: string;
  status: "conforme" | "parziale" | "non_conforme" | "non_applicabile";
  note: string | null;
  updated_at: string;
}

export interface ComplianceScore {
  score_percent: number;
  measures_conformi: number;
  measures_parziali: number;
  measures_non_conformi: number;
  measures_non_applicabili: number;
  measures_total: number;
}

export interface ComplianceHistoryPoint {
  recorded_at: string;
  score_percent: number;
}

export function useComplianceMeasures() {
  const api = useApi();
  return useQuery<ComplianceMeasure[]>({
    queryKey: ["compliance", "measures"],
    queryFn: () => api.get("/compliance/measures"),
  });
}

export function useComplianceScore() {
  const api = useApi();
  return useQuery<ComplianceScore>({
    queryKey: ["compliance", "score"],
    queryFn: () => api.get("/compliance/score"),
  });
}

export function useComplianceHistory() {
  const api = useApi();
  return useQuery<ComplianceHistoryPoint[]>({
    queryKey: ["compliance", "history"],
    queryFn: () => api.get("/compliance/history"),
  });
}

export function useUpdateComplianceMeasure() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      measureId,
      status,
      note,
    }: {
      measureId: string;
      status: string;
      note?: string | null;
    }) => api.patch(`/compliance/measures/${measureId}`, { status, note: note ?? null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
