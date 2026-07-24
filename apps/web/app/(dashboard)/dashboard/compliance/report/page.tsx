"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { complianceCategoryOf } from "@/lib/complianceCategories";
import { formatDateTime } from "@/lib/format";
import { useComplianceMeasures, useComplianceScore } from "@/lib/queries/compliance";

const STATUS_LABELS: Record<string, string> = {
  conforme: "Conforme",
  parziale: "Parziale",
  non_conforme: "Non conforme",
  non_applicabile: "Non applicabile",
};

/**
 * Report stampabile del Compliance Tracker: la roadmap Fase 4 chiede un pulsante
 * "Esporta report conformità PDF". Invece di generare il PDF lato server (motore di
 * rendering dedicato, storage, ecc. — sproporzionato per un report generato al volo),
 * questa pagina è pensata per essere stampata dal browser ("Stampa" → "Salva come PDF"):
 * stesso risultato per l'utente, zero dipendenze nuove lato backend.
 */
export default function ComplianceReportPage() {
  const measuresQuery = useComplianceMeasures();
  const scoreQuery = useComplianceScore();

  if (measuresQuery.isLoading || scoreQuery.isLoading) {
    return <Skeleton className="h-96 w-full" />;
  }

  const measures = measuresQuery.data ?? [];
  const score = scoreQuery.data;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 bg-white p-4 print:p-0">
      <div className="flex items-center justify-between print:hidden">
        <h1 className="text-xl font-bold text-brand-dark">Report Conformità</h1>
        <button
          onClick={() => window.print()}
          className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
        >
          Stampa / Salva come PDF
        </button>
      </div>

      <header className="border-b border-slate-300 pb-4">
        <p className="text-2xl font-bold text-brand-dark">
          CyberComply<span className="text-brand-amber">IT</span>
        </p>
        <h2 className="mt-2 text-lg font-semibold text-slate-800">
          Report di conformità NIS2 / Det. ACN 164179/2025
        </h2>
        <p className="text-sm text-slate-500">Generato il {formatDateTime(new Date().toISOString())}</p>
      </header>

      {score && (
        <section>
          <h3 className="mb-2 font-semibold text-slate-800">Sintesi</h3>
          <p className="text-3xl font-bold text-brand-dark">{score.score_percent}%</p>
          <p className="text-sm text-slate-600">
            {score.measures_conformi} misure conformi, {score.measures_parziali} parziali,{" "}
            {score.measures_non_conformi} non conformi, {score.measures_non_applicabili} non
            applicabili su {score.measures_total} totali.
          </p>
        </section>
      )}

      <section>
        <h3 className="mb-2 font-semibold text-slate-800">Dettaglio misure</h3>
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
              <th className="py-2 pr-2">Misura</th>
              <th className="py-2 pr-2">Categoria</th>
              <th className="py-2 pr-2">Stato</th>
              <th className="py-2">Note</th>
            </tr>
          </thead>
          <tbody>
            {measures.map((m) => (
              <tr key={m.measure_id} className="border-b border-slate-200 align-top">
                <td className="py-2 pr-2 font-medium text-slate-800">{m.label}</td>
                <td className="py-2 pr-2 text-slate-600">{complianceCategoryOf(m.measure_id)}</td>
                <td className="py-2 pr-2 text-slate-600">{STATUS_LABELS[m.status]}</td>
                <td className="py-2 text-slate-600">{m.note ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <footer className="mt-6 text-xs text-slate-500">
        Report generato automaticamente da CyberComplyIT. Non costituisce parere legale.
      </footer>
    </div>
  );
}
