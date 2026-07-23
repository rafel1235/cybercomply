"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiFetchPublic, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { QUESTIONNAIRE_QUESTION_LABELS, SUPPLIER_STATUS_LABELS, SUPPLIER_STATUS_VARIANTS } from "@/lib/supplierLabels";

/** Rispecchia il calcolo di app/services/supplier_scoring.py: la risposta pubblica non
 * include lo stato calcolato (vista intenzionalmente minimale), quindi lo si ricava qui
 * dalle stesse risposte per mostrare una conferma coerente con quanto registrato lato
 * organizzazione. */
function computeStatusPreview(
  answers: Record<string, unknown>,
  questions: string[]
): string {
  const positiveCount = questions.filter((q) => answers[q] === true).length;
  if (positiveCount === questions.length) return "conforme";
  if (positiveCount === 0) return "non_conforme";
  return "parziale";
}

interface QuestionnairePublic {
  supplier_name: string;
  questions: string[];
  answers: Record<string, unknown>;
  completed_at: string | null;
}

/**
 * Pagina pubblica di compilazione del questionario fornitori: nessun account richiesto,
 * il possesso del link (contenente il token) è di per sé la credenziale, come da design
 * del backend (app/api/v1/routes/public_questionnaires.py). Vive fuori dal gruppo
 * (dashboard), quindi non passa dal layout con guardia di autenticazione.
 */
export default function PublicQuestionnairePage() {
  const params = useParams<{ token: string }>();
  const [questionnaire, setQuestionnaire] = useState<QuestionnairePublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [computedStatus, setComputedStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data: QuestionnairePublic = await apiFetchPublic(
          `/public/questionnaires/${params.token}`
        );
        if (cancelled) return;
        setQuestionnaire(data);
        setComputedStatus(
          data.completed_at ? computeStatusPreview(data.answers, data.questions) : null
        );
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [params.token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      const result: QuestionnairePublic = await apiFetchPublic(
        `/public/questionnaires/${params.token}`,
        { method: "POST", body: JSON.stringify({ answers }) }
      );
      setQuestionnaire(result);
      setComputedStatus(
        result.completed_at ? computeStatusPreview(result.answers, result.questions) : null
      );
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Errore durante l'invio. Riprova."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-6 px-4 py-12">
      <div className="text-center">
        <p className="text-2xl font-bold text-brand-dark">
          CyberComply<span className="text-brand-amber">IT</span>
        </p>
        <p className="mt-1 text-sm text-slate-500">Questionario di sicurezza fornitori</p>
      </div>

      {loading ? (
        <Skeleton className="h-64 w-full" />
      ) : notFound ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-600">
          Questionario non trovato. Verifica di aver copiato correttamente il link ricevuto.
        </div>
      ) : questionnaire?.completed_at ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-slate-200 bg-white p-6 text-center">
          <p className="font-medium text-slate-800">Questionario già inviato</p>
          <p className="text-sm text-slate-500">
            Compilato il {formatDateTime(questionnaire.completed_at)} per{" "}
            <strong>{questionnaire.supplier_name}</strong>.
          </p>
          {computedStatus && (
            <Badge
              label={SUPPLIER_STATUS_LABELS[computedStatus] ?? computedStatus}
              variant={SUPPLIER_STATUS_VARIANTS[computedStatus] ?? "neutral"}
            />
          )}
          <p className="text-xs text-slate-400">
            Grazie per aver completato la valutazione. Non è necessaria nessuna altra azione.
          </p>
        </div>
      ) : questionnaire ? (
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-5 rounded-lg border border-slate-200 bg-white p-6"
        >
          <p className="text-sm text-slate-600">
            Per conto di <strong>{questionnaire.supplier_name}</strong>, rispondi alle seguenti
            domande sui controlli di sicurezza in essere. Le risposte determinano lo stato di
            conformità registrato nel nostro tracker fornitori.
          </p>
          <div className="flex flex-col gap-3">
            {questionnaire.questions.map((question) => (
              <label
                key={question}
                className="flex items-start gap-3 rounded-md border border-slate-200 p-3 text-sm text-slate-700"
              >
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={answers[question] ?? false}
                  onChange={(e) =>
                    setAnswers((a) => ({ ...a, [question]: e.target.checked }))
                  }
                />
                {QUESTIONNAIRE_QUESTION_LABELS[question] ?? question}
              </label>
            ))}
          </div>
          {submitError && <p className="text-sm text-red-600">{submitError}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
          >
            {submitting ? "Invio in corso…" : "Invia risposte"}
          </button>
        </form>
      ) : null}
    </div>
  );
}
