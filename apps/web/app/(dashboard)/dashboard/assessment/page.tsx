"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDateTime } from "@/lib/format";
import {
  type AssessmentAnswers,
  useAssessmentHistory,
  useCreateAssessment,
  useLatestAssessment,
} from "@/lib/queries/assessments";
import { useToast } from "@/lib/toast";

const NIS2_BADGE: Record<string, { label: string; variant: "danger" | "warning" | "neutral" }> = {
  essenziale: { label: "Soggetto essenziale", variant: "danger" },
  importante: { label: "Soggetto importante", variant: "warning" },
  non_in_perimetro: { label: "Fuori perimetro", variant: "neutral" },
};

const DEFAULT_ANSWERS: AssessmentAnswers = {
  sector_annex: "nessuno",
  employee_count: 0,
  annual_revenue_eur: 0,
  supplies_ict_to_regulated_entities: false,
  produces_digital_product_for_eu_market: false,
};

export default function AssessmentPage() {
  const { showToast } = useToast();
  const latestQuery = useLatestAssessment();
  const historyQuery = useAssessmentHistory();
  const createMutation = useCreateAssessment();

  const [answers, setAnswers] = useState<AssessmentAnswers>(DEFAULT_ANSWERS);
  const [showForm, setShowForm] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createMutation.mutateAsync(answers);
      showToast("Assessment completato: risultato salvato.", "success");
      setShowForm(false);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'assessment", "error");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-brand-dark">Assessment NIS2 / CRA</h1>
        {!showForm && (
          <button
            onClick={() => {
              setAnswers(DEFAULT_ANSWERS);
              setShowForm(true);
            }}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
          >
            {latestQuery.data ? "Rifai l'assessment" : "Esegui l'assessment"}
          </button>
        )}
      </div>

      {showForm ? (
        <form
          onSubmit={handleSubmit}
          className="flex max-w-xl flex-col gap-5 rounded-lg border border-slate-200 bg-white p-6"
        >
          <fieldset className="flex flex-col gap-2">
            <legend className="text-sm font-semibold text-slate-700">
              La tua azienda rientra in uno degli Allegati NIS2?
            </legend>
            {(
              [
                ["allegato_i", "Sì, Allegato I (soggetti essenziali)"],
                ["allegato_ii", "Sì, Allegato II (soggetti importanti)"],
                ["nessuno", "No, nessuno dei due"],
              ] as const
            ).map(([value, label]) => (
              <label key={value} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="radio"
                  name="sector_annex"
                  checked={answers.sector_annex === value}
                  onChange={() => setAnswers((a) => ({ ...a, sector_annex: value }))}
                />
                {label}
              </label>
            ))}
          </fieldset>

          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Numero di dipendenti
            <input
              type="number"
              min={0}
              value={answers.employee_count}
              onChange={(e) =>
                setAnswers((a) => ({ ...a, employee_count: Number(e.target.value) }))
              }
              className="rounded-md border border-slate-300 px-3 py-2 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Fatturato o bilancio annuo (EUR)
            <input
              type="number"
              min={0}
              value={answers.annual_revenue_eur}
              onChange={(e) =>
                setAnswers((a) => ({ ...a, annual_revenue_eur: Number(e.target.value) }))
              }
              className="rounded-md border border-slate-300 px-3 py-2 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={answers.supplies_ict_to_regulated_entities}
              onChange={(e) =>
                setAnswers((a) => ({
                  ...a,
                  supplies_ict_to_regulated_entities: e.target.checked,
                }))
              }
            />
            Forniamo prodotti/servizi ICT a soggetti già regolati da NIS2
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={answers.produces_digital_product_for_eu_market}
              onChange={(e) =>
                setAnswers((a) => ({
                  ...a,
                  produces_digital_product_for_eu_market: e.target.checked,
                }))
              }
            />
            Produciamo o vendiamo prodotti con elementi digitali nel mercato UE
          </label>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
            >
              {createMutation.isPending ? "Calcolo in corso…" : "Calcola risultato"}
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
      ) : latestQuery.isLoading ? (
        <Skeleton className="h-40 w-full max-w-xl" />
      ) : latestQuery.data ? (
        <div className="flex max-w-xl flex-col gap-3 rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <Badge
              label={NIS2_BADGE[latestQuery.data.nis2_category].label}
              variant={NIS2_BADGE[latestQuery.data.nis2_category].variant}
            />
            <Badge
              label={latestQuery.data.cra_in_scope ? "CRA: in perimetro" : "CRA: non in perimetro"}
              variant={latestQuery.data.cra_in_scope ? "warning" : "neutral"}
            />
          </div>
          {latestQuery.data.rationale && (
            <p className="text-sm text-slate-600">{latestQuery.data.rationale}</p>
          )}
          <p className="text-xs text-slate-500">
            Ultimo assessment eseguito il {formatDateTime(latestQuery.data.created_at)}
          </p>
        </div>
      ) : (
        <EmptyState
          title="Nessun assessment ancora eseguito"
          description="Rispondi a poche domande per scoprire se la tua azienda rientra nel perimetro NIS2 e/o CRA."
        />
      )}

      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-slate-800">Storico assessment</h2>
        {historyQuery.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !historyQuery.data || historyQuery.data.length === 0 ? (
          <p className="text-sm text-slate-500">Nessuno storico disponibile.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Data</th>
                  <th className="px-4 py-2">Categoria NIS2</th>
                  <th className="px-4 py-2">CRA</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {historyQuery.data.map((result) => (
                  <tr key={result.id}>
                    <td className="px-4 py-2 text-slate-600">
                      {formatDateTime(result.created_at)}
                    </td>
                    <td className="px-4 py-2">
                      <Badge
                        label={NIS2_BADGE[result.nis2_category].label}
                        variant={NIS2_BADGE[result.nis2_category].variant}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <Badge
                        label={result.cra_in_scope ? "In perimetro" : "Non in perimetro"}
                        variant={result.cra_in_scope ? "warning" : "neutral"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
