"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

export interface DocumentSection {
  titolo: string;
  corpo: string;
}

export interface DocumentContent {
  generato_da?: string;
  nota?: string;
  sezioni: DocumentSection[];
}

export interface DocumentItem {
  id: string;
  doc_type: string;
  content: DocumentContent;
  pdf_url: string | null;
  version: number;
  created_at: string;
}

export function useDocuments(docType?: string) {
  const api = useApi();
  return useQuery<DocumentItem[]>({
    queryKey: ["documents", docType ?? "all"],
    queryFn: () => api.get(docType ? `/documents?doc_type=${docType}` : "/documents"),
  });
}

export function useGenerateDocument() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docType: string) => api.post("/documents/generate", { doc_type: docType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useGenerateDocumentPdf() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => api.post(`/documents/${documentId}/pdf`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocument() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => api.del(`/documents/${documentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

/** Scarica il PDF già generato e lo salva come file sul dispositivo dell'utente,
 * creando un link temporaneo in memoria (nessun nuovo tab, nessuna navigazione). */
export function useDownloadDocumentPdf() {
  const api = useApi();
  return useMutation({
    mutationFn: async ({ documentId, fileName }: { documentId: string; fileName: string }) => {
      const blob = await api.getBlob(`/documents/${documentId}/pdf`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });
}
