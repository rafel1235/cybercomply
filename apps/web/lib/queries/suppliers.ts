"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export interface SupplierQuestionnaire {
  id: string;
  answers: Record<string, unknown>;
  computed_status: string;
  access_token: string;
  sent_at: string | null;
  completed_at: string | null;
}

export interface Supplier {
  id: string;
  name: string;
  category: string | null;
  criticality: string;
  status: string;
  last_reviewed_at: string | null;
  created_at: string;
  questionnaires: SupplierQuestionnaire[];
}

export function useSuppliers() {
  const api = useApi();
  return useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: () => api.get("/suppliers"),
  });
}

export function useSupplier(id: string) {
  const api = useApi();
  return useQuery<Supplier>({
    queryKey: ["suppliers", "detail", id],
    queryFn: () => api.get(`/suppliers/${id}`),
    enabled: Boolean(id),
  });
}

export function useCreateSupplier() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; category?: string; criticality: string }) =>
      api.post("/suppliers", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useUpdateSupplier() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: string;
      name?: string;
      category?: string;
      criticality?: string;
      status?: string;
    }) => api.put(`/suppliers/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useDeleteSupplier() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del(`/suppliers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useCreateQuestionnaire() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (supplierId: string) => api.post(`/suppliers/${supplierId}/questionnaires`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
