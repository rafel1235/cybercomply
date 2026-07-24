"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export type Plan = "free" | "essential" | "business" | "enterprise";
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "canceled";

export interface Entitlements {
  max_users: number | null;
  max_ai_documents_per_month: number | null;
  compliance_measures_limit: number | null;
  compliance_measures_editable: boolean;
  incident_reporting_enabled: boolean;
  supply_chain_enabled: boolean;
  quarterly_reports_enabled: boolean;
  white_label_enabled: boolean;
  api_access_enabled: boolean;
}

export interface Usage {
  documents_generated_this_month: number;
  users_count: number;
}

export interface Subscription {
  plan: Plan;
  status: SubscriptionStatus;
  trial_ends_at: string | null;
  renews_at: string | null;
  entitlements: Entitlements;
  usage: Usage;
}

/** Stato abbonamento, limiti del piano e utilizzo corrente. Usato sia dalla pagina
 * Impostazioni > Fatturazione sia dagli indicatori di gating sparsi nella dashboard
 * (nav bloccata, quota documenti, misure in sola lettura). */
export function useSubscription() {
  const api = useApi();
  return useQuery<Subscription>({
    queryKey: ["billing", "subscription"],
    queryFn: () => api.get("/billing/subscription"),
  });
}

export function useCheckout() {
  const api = useApi();
  return useMutation({
    mutationFn: (plan: Plan) =>
      api.post("/billing/checkout", { plan }) as Promise<{ checkout_url: string }>,
  });
}

export function usePortal() {
  const api = useApi();
  return useMutation({
    mutationFn: () => api.post("/billing/portal") as Promise<{ portal_url: string }>,
  });
}

export function invalidateBilling(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["billing"] });
}
