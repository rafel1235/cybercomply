"use client";

import { useMutation } from "@tanstack/react-query";
import { useApi } from "@/lib/useApi";

/** Scarica l'export GDPR completo (Art. 20 — diritto alla portabilità dei dati, Fase 8)
 * come file JSON, con lo stesso pattern già usato per il download dei PDF dei documenti:
 * nessuna navigazione, nessun nuovo tab, solo un link temporaneo in memoria. */
export function useExportMyData() {
  const api = useApi();
  return useMutation({
    mutationFn: async () => {
      const data = await api.get("/gdpr/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const today = new Date().toISOString().slice(0, 10);
      link.href = url;
      link.download = `cybercomplyit-export-dati-${today}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });
}

export interface GdprAccountDeletionResult {
  deleted_at: string;
  organizations_deleted: string[];
  organizations_left: string[];
  auth_account_deleted: boolean;
}

/** Cancella l'account (GDPR Art. 17 — diritto alla cancellazione, Fase 8). Chiamata
 * distruttiva e irreversibile: la conferma esplicita (l'utente deve digitare una parola)
 * è responsabilità del componente che usa questo hook, non di questo hook stesso. */
export function useDeleteMyAccount() {
  const api = useApi();
  return useMutation({
    mutationFn: (): Promise<GdprAccountDeletionResult> => api.del("/gdpr/account"),
  });
}
