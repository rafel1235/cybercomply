"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { UpsellNotice } from "@/components/ui/UpsellNotice";
import { ApiError } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import {
  useCreateQuestionnaire,
  useCreateSupplier,
  useDeleteSupplier,
  useSuppliers,
  useUpdateSupplier,
  type Supplier,
} from "@/lib/queries/suppliers";
import {
  SUPPLIER_CRITICALITY_LABELS,
  SUPPLIER_CRITICALITY_VARIANTS,
  SUPPLIER_STATUS_LABELS,
  SUPPLIER_STATUS_VARIANTS,
} from "@/lib/supplierLabels";
import { useToast } from "@/lib/toast";

const CRITICALITY_OPTIONS = ["alta", "media", "bassa"];

export default function SuppliersPage() {
  const { showToast } = useToast();
  const suppliersQuery = useSuppliers();
  const createMutation = useCreateSupplier();
  const updateMutation = useUpdateSupplier();
  const deleteMutation = useDeleteSupplier();
  const questionnaireMutation = useCreateQuestionnaire();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [criticality, setCriticality] = useState("media");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      showToast("Indica il nome del fornitore", "error");
      return;
    }
    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        category: category.trim() || undefined,
        criticality,
      });
      showToast("Fornitore aggiunto.", "success");
      setName("");
      setCategory("");
      setCriticality("media");
      setShowForm(false);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante il salvataggio", "error");
    }
  }

  async function handleCriticalityChange(supplier: Supplier, value: string) {
    try {
      await updateMutation.mutateAsync({ id: supplier.id, criticality: value });
      showToast("Criticità aggiornata.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'aggiornamento", "error");
    }
  }

  async function handleDelete(supplier: Supplier) {
    if (!window.confirm(`Eliminare il fornitore "${supplier.name}"?`)) return;
    try {
      await deleteMutation.mutateAsync(supplier.id);
      showToast("Fornitore eliminato.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'eliminazione", "error");
    }
  }

  async function handleSendQuestionnaire(supplier: Supplier) {
    try {
      const questionnaire = await questionnaireMutation.mutateAsync(supplier.id);
      const link = `${window.location.origin}/questionario/${questionnaire.access_token}`;
      try {
        await navigator.clipboard.writeText(link);
        showToast("Questionario creato: link copiato negli appunti.", "success");
      } catch {
        showToast(`Questionario creato. Link: ${link}`, "info");
      }
      setExpandedId(supplier.id);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore nella creazione", "error");
    }
  }

  async function copyLink(token: string) {
    const link = `${window.location.origin}/questionario/${token}`;
    try {
      await navigator.clipboard.writeText(link);
      showToast("Link copiato negli appunti.", "success");
    } catch {
      showToast(`Link: ${link}`, "info");
    }
  }

  const suppliers = suppliersQuery.data ?? [];

  const blockedByPlan =
    suppliersQuery.isError &&
    suppliersQuery.error instanceof ApiError &&
    suppliersQuery.error.status === 403;

  if (blockedByPlan) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-brand-dark">Supply Chain</h1>
        <UpsellNotice
          title="Modulo non incluso nel tuo piano attuale"
          description="Il monitoraggio dei fornitori (questionari di sicurezza, criticità, stato di conformità) è incluso dal piano Business in su."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-brand-dark">Supply Chain</h1>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
          >
            Aggiungi fornitore
          </button>
        )}
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="flex max-w-xl flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6"
        >
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Nome fornitore
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Categoria (opzionale)
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="Es. hosting, software gestionale, consulenza…"
              className="rounded-md border border-slate-300 px-3 py-2 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
          </label>
          <fieldset className="flex flex-col gap-2">
            <legend className="text-sm font-semibold text-slate-700">Criticità</legend>
            {CRITICALITY_OPTIONS.map((value) => (
              <label key={value} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="radio"
                  name="criticality"
                  checked={criticality === value}
                  onChange={() => setCriticality(value)}
                />
                {SUPPLIER_CRITICALITY_LABELS[value]}
              </label>
            ))}
          </fieldset>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
            >
              {createMutation.isPending ? "Salvataggio…" : "Salva"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Annulla
            </button>
          </div>
        </form>
      )}

      {suppliersQuery.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : suppliers.length === 0 ? (
        <EmptyState
          title="Nessun fornitore registrato"
          description="Aggiungi i fornitori critici e invia loro un questionario di sicurezza: non serve un account per compilarlo."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {suppliers.map((supplier) => {
            const latestQuestionnaire = supplier.questionnaires[0];
            const expanded = expandedId === supplier.id;
            return (
              <div key={supplier.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-800">{supplier.name}</p>
                    {supplier.category && (
                      <p className="text-xs text-slate-500">{supplier.category}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      aria-label={`Criticità di ${supplier.name}`}
                      value={supplier.criticality}
                      onChange={(e) => handleCriticalityChange(supplier, e.target.value)}
                      className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                    >
                      {CRITICALITY_OPTIONS.map((value) => (
                        <option key={value} value={value}>
                          Criticità: {SUPPLIER_CRITICALITY_LABELS[value]}
                        </option>
                      ))}
                    </select>
                    <Badge
                      label={SUPPLIER_STATUS_LABELS[supplier.status] ?? supplier.status}
                      variant={SUPPLIER_STATUS_VARIANTS[supplier.status] ?? "neutral"}
                    />
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button
                    onClick={() => handleSendQuestionnaire(supplier)}
                    disabled={questionnaireMutation.isPending}
                    className="rounded-md bg-brand-blue px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
                  >
                    Invia questionario
                  </button>
                  {supplier.questionnaires.length > 0 && (
                    <button
                      onClick={() => setExpandedId(expanded ? null : supplier.id)}
                      className="text-xs font-medium text-brand-blue hover:underline"
                    >
                      {expanded
                        ? "Nascondi questionari"
                        : `Questionari (${supplier.questionnaires.length})`}
                    </button>
                  )}
                  {supplier.last_reviewed_at && (
                    <span className="text-xs text-slate-500">
                      Ultima revisione: {formatDate(supplier.last_reviewed_at)}
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(supplier)}
                    className="ml-auto text-xs font-medium text-red-600 hover:underline"
                  >
                    Elimina
                  </button>
                </div>

                {expanded && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-slate-100 pt-3">
                    {supplier.questionnaires.map((q) => (
                      <div
                        key={q.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs"
                      >
                        <span className="text-slate-600">
                          Inviato: {formatDateTime(q.sent_at)}
                          {q.completed_at
                            ? ` · Completato: ${formatDateTime(q.completed_at)}`
                            : " · In attesa di risposta"}
                        </span>
                        <div className="flex items-center gap-2">
                          {q.completed_at && (
                            <Badge
                              label={SUPPLIER_STATUS_LABELS[q.computed_status] ?? q.computed_status}
                              variant={SUPPLIER_STATUS_VARIANTS[q.computed_status] ?? "neutral"}
                            />
                          )}
                          {!q.completed_at && (
                            <button
                              onClick={() => copyLink(q.access_token)}
                              className="font-medium text-brand-blue hover:underline"
                            >
                              Copia link
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                    {latestQuestionnaire === undefined && (
                      <p className="text-xs text-slate-500">Nessun questionario ancora inviato.</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
