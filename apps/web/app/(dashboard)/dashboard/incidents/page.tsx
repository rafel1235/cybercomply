"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { UpsellNotice } from "@/components/ui/UpsellNotice";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_VARIANTS } from "@/lib/incidentLabels";
import { useCreateIncident, useIncidents } from "@/lib/queries/incidents";
import { useToast } from "@/lib/toast";

const STATUS_FILTERS = [
  ["", "Tutti"],
  ["aperto", "Aperti"],
  ["in_gestione", "In gestione"],
  ["chiuso", "Chiusi"],
] as const;

export default function IncidentsPage() {
  const { showToast } = useToast();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [incidentType, setIncidentType] = useState("");
  const [descrizione, setDescrizione] = useState("");

  const incidentsQuery = useIncidents(statusFilter || undefined);
  const createMutation = useCreateIncident();

  const blockedByPlan =
    incidentsQuery.isError &&
    incidentsQuery.error instanceof ApiError &&
    incidentsQuery.error.status === 403;

  const filtered = useMemo(() => {
    const list = incidentsQuery.data ?? [];
    if (!search.trim()) return list;
    const q = search.trim().toLowerCase();
    return list.filter(
      (i) =>
        i.incident_type.toLowerCase().includes(q) ||
        i.reference_code.toLowerCase().includes(q)
    );
  }, [incidentsQuery.data, search]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!incidentType.trim()) {
      showToast("Indica la tipologia di incidente", "error");
      return;
    }
    try {
      await createMutation.mutateAsync({
        incident_type: incidentType.trim(),
        data: descrizione.trim() ? { descrizione: descrizione.trim() } : undefined,
      });
      showToast("Incidente aperto: scadenze di notifica calcolate.", "success");
      setIncidentType("");
      setDescrizione("");
      setShowForm(false);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'apertura", "error");
    }
  }

  if (blockedByPlan) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-brand-dark">Gestione incidenti</h1>
        <UpsellNotice
          title="Modulo non incluso nel tuo piano attuale"
          description="L'Incident Reporting (scadenze di notifica NIS2/CRA, checklist e bozze email per CSIRT/ENISA) è incluso dal piano Essential in su."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-brand-dark">Gestione incidenti</h1>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
          >
            Apri incidente
          </button>
        )}
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="flex max-w-xl flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6"
        >
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Tipologia di incidente
            <input
              type="text"
              value={incidentType}
              onChange={(e) => setIncidentType(e.target.value)}
              placeholder="Es. accesso non autorizzato, ransomware, data breach…"
              className="rounded-md border border-slate-300 px-3 py-2 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Descrizione (opzionale)
            <textarea
              value={descrizione}
              onChange={(e) => setDescrizione(e.target.value)}
              rows={3}
              className="rounded-md border border-slate-300 px-3 py-2 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
          </label>
          <p className="text-xs text-slate-500">
            All&apos;apertura vengono calcolate automaticamente le scadenze di notifica NIS2/CRA
            applicabili.
          </p>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
            >
              {createMutation.isPending ? "Apertura in corso…" : "Apri incidente"}
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

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-2" role="group" aria-label="Filtra per stato">
          {STATUS_FILTERS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={statusFilter === value}
              onClick={() => setStatusFilter(value)}
              className={`rounded-full px-3 py-1 text-sm font-medium ${
                statusFilter === value
                  ? "bg-brand-blue text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          type="text"
          aria-label="Cerca incidenti per tipologia o codice"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cerca per tipologia o codice…"
          className="ml-auto w-64 rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
        />
      </div>

      {incidentsQuery.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Nessun incidente trovato"
          description="Quando apri un incidente, qui compariranno codice, stato e scadenze di notifica."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Codice</th>
                <th className="px-4 py-2">Tipologia</th>
                <th className="px-4 py-2">Stato</th>
                <th className="px-4 py-2">Apertura</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((incident) => (
                <tr key={incident.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <Link
                      href={`/dashboard/incidents/${incident.id}`}
                      className="font-medium text-brand-blue hover:underline"
                    >
                      {incident.reference_code}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-700">{incident.incident_type}</td>
                  <td className="px-4 py-2">
                    <Badge
                      label={INCIDENT_STATUS_LABELS[incident.status] ?? incident.status}
                      variant={INCIDENT_STATUS_VARIANTS[incident.status] ?? "neutral"}
                    />
                  </td>
                  <td className="px-4 py-2 text-slate-600">{formatDateTime(incident.opened_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
