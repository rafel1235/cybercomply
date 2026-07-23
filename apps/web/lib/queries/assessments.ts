"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";

export interface AssessmentAnswers {
  sector_annex: "allegato_i" | "allegato_ii" | "nessuno";
  employee_count: number;
  annual_revenue_eur: number;
  supplies_ict_to_regulated_entities: boolean;
  produces_digital_product_for_eu_market: boolean;
}

export interface AssessmentResult {
  id: string;
  nis2_category: "essenziale" | "importante" | "non_in_perimetro";
  cra_in_scope: boolean;
  answers: AssessmentAnswers;
  rationale: string | null;
  created_at: string;
}

export function useLatestAssessment() {
  const api = useApi();
  return useQuery<AssessmentResult | null>({
    queryKey: ["assessments", "latest"],
    queryFn: async () => {
      try {
        return await api.get("/assessments/latest");
      } catch (err) {
        // Nessun assessment ancora eseguito: stato legittimo per un'organizzazione
        // appena creata, non un errore da propagare come toast.
        if (err instanceof ApiError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
  });
}

export function useAssessmentHistory() {
  const api = useApi();
  return useQuery<AssessmentResult[]>({
    queryKey: ["assessments", "history"],
    queryFn: () => api.get("/assessments"),
  });
}

export function useCreateAssessment() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (answers: AssessmentAnswers) => api.post("/assessments", { answers }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
