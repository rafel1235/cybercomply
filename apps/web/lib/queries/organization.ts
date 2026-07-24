"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export interface OrganizationMember {
  user_id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "viewer";
  joined_at: string;
}

export function useOrganizationMembers() {
  const api = useApi();
  return useQuery<OrganizationMember[]>({
    queryKey: ["organization", "members"],
    queryFn: () => api.get("/organization/members"),
  });
}

export function useInviteMember() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; role: string }) =>
      api.post("/organization/invites", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      // L'invito conta ai fini del limite posti del piano: l'utilizzo mostrato nella
      // pagina Fatturazione deve aggiornarsi subito.
      queryClient.invalidateQueries({ queryKey: ["billing"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useRemoveMember() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.del(`/organization/members/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      queryClient.invalidateQueries({ queryKey: ["billing"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
