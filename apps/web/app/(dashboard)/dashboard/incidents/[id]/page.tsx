"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDateTime } from "@/lib/format";
import { buildNotificationEmailDraft } from "@/lib/incidentEmailTemplate";
import {
  INCIDENT_STATUS_LABELS,
  INCIDENT_STATUS_VARIANTS,
  NOTIFICATION_PHASE_DEFAULT_RECIPIENT,
  NOTIFICATION_PHASE_LABELS,
} from "@/lib/incidentLabels";
import { useCloseIncident, useIncident, useRecordNotification } from "@/lib/queries/incidents";
import { useToast } from "@/lib/toast";

/** Timer live che mostra il tempo trascorso dall'apertura, ricalcolato ad ogni tick dal
 * timestamp reale del server (non salvato lato client): sopravvive quindi a un refresh. */
function useElapsedSince(openedAt: string | undefined): string {
  const [, forceTick] = useState(0);

  useEffect(() => {
    if (!openedAt) return;
    const interval = setInterval(() => forceTick((n) => n + 1), 1000);
    return () => clearInterval(interval);
  }, [openedAt]);

  if (!openedAt) return "—";
  const diffMs = Date.now() - new Date(openedAt).getTime();
  if (diffMs < 0) return "0s";
  const totalSeconds = Math.floor(diffMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts: string[] = [];
  if (days > 0) parts.push(`${days}g`);
  if (days > 0 || hours > 0) parts.push(`${hours}h`);
  parts.push(`${minutes}m`);
  parts.push(`${seconds}s`);
  return parts.join(" ");
}

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { showToast } = useToast();
  const incidentQuery = useIncident(params.id);
  const closeMutation = useCloseIncident();
  const recordMutation = useRecordNotification();

  const [notifyPhase, setNotifyPhase] = useState<string | null>(null);
  const [recipient, setRecipient] = useState("");
  const [content, setContent] = useState("");
  const [draftPhase, setDraftPhase] = useState<string | null>(null);

  const incident = incidentQuery.data;
  const elapsed = useElapsedSince(incident?.opened_at);

  if (incidentQuery.isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!incident) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-slate-500">Incidente non trovato.</p>
        <button
          onClick={() => router.push("/dashboard/incidents")}
          className="w-fit rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Torna all&apos;elenco
        </button>
      </div>
    );
  }

  function openNotifyForm(phase: string) {
    setNotifyPhase(phase);
    setRecipient(NOTIFICATION_PHASE_DEFAULT_RECIPIENT[phase] ?? "");
    setContent("");
  }

  async function handleRecordNotification(e: React.FormEvent) {
    e.preventDefault();
    if (!notifyPhase || !incident) return;
    if (!recipient.trim()) {
      showToast("Indica il destinatario della notifica", "error");
      return;
    }
    try {
      await recordMutation.mutateAsync({
        incidentId: incident.id,
        phase: notifyPhase,
        recipient: recipient.trim(),
        content: content.trim() || undefined,
      });
      showToast("Notifica registrata.", "success");
      setNotifyPhase(null);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore nella registrazione", "error");
    }
  }

  async function handleClose() {
    if (!incident) return;
    if (!window.confirm("Confermi la chiusura dell'incidente? L'operazione è definitiva.")) {
      return;
    }
    try {
      await closeMutation.mutateAsync(incident.id);
      showToast("Incidente chiuso.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore nella chiusura", "error");
    }
  }

  async function copyDraft() {
    if (!draftPhase || !incident) return;
    const { subject, body } = buildNotificationEmailDraft(incident, draftPhase);
    try {
      await navigator.clipboard.writeText(`Oggetto: ${subject}\n\n${body}`);
      showToast("Bozza copiata negli appunti.", "success");
    } catch {
      showToast("Impossibile copiare automaticamente: seleziona e copia il testo.", "info");
    }
  }

  const draft = draftPhase ? buildNotificationEmailDraft(incident, draftPhase) : null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between print:hidden">
        <div>
          <h1 className="text-2xl font-bold text-brand-dark">{incident.reference_code}</h1>
          <p className="text-sm text-slate-500">{incident.incident_type}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => window.print()}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Stampa / Esporta PDF
          </button>
          {incident.status !== "chiuso" && (
            <button
              onClick={handleClose}
              disabled={closeMutation.isPending}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
            >
              Chiudi incidente
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase text-slate-500">Stato</p>
          <Badge
            label={INCIDENT_STATUS_LABELS[incident.status] ?? incident.status}
            variant={INCIDENT_STATUS_VARIANTS[incident.status] ?? "neutral"}
          />
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase text-slate-500">Aperto il</p>
          <p className="font-medium text-slate-800">{formatDateTime(incident.opened_at)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase text-slate-500">
            {incident.status === "chiuso" ? "Tempo totale" : "Tempo trascorso"}
          </p>
          <p className="font-mono text-lg font-semibold text-brand-dark">
            {incident.status === "chiuso" && incident.closed_at
              ? (() => {
                  const ms =
                    new Date(incident.closed_at).getTime() - new Date(incident.opened_at).getTime();
                  const h = Math.floor(ms / 3600000);
                  const m = Math.floor((ms % 3600000) / 60000);
                  return `${h}h ${m}m`;
                })()
              : elapsed}
          </p>
        </div>
      </div>

      {incident.data?.descrizione ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="mb-1 text-xs uppercase text-slate-500">Descrizione</p>
          <p className="text-sm text-slate-700">{String(incident.data.descrizione)}</p>
        </div>
      ) : null}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-slate-800">Scadenze di notifica</h2>
        <div className="flex flex-col gap-3">
          {incident.deadlines.map((deadline) => {
            const notification = incident.notifications.find((n) => n.phase === deadline.phase);
            return (
              <div
                key={deadline.phase}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-800">
                      {NOTIFICATION_PHASE_LABELS[deadline.phase] ?? deadline.phase}
                    </p>
                    <p className="text-xs text-slate-500">
                      Scadenza: {formatDateTime(deadline.due_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 print:hidden">
                    {deadline.sent ? (
                      <Badge label="Notificato" variant="success" />
                    ) : deadline.overdue ? (
                      <Badge label="Scaduto" variant="danger" />
                    ) : (
                      <Badge label="In attesa" variant="warning" />
                    )}
                    {!deadline.sent && (
                      <>
                        <button
                          onClick={() => setDraftPhase(deadline.phase)}
                          className="rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                        >
                          Bozza email
                        </button>
                        <button
                          onClick={() => openNotifyForm(deadline.phase)}
                          className="rounded-md bg-brand-blue px-3 py-1 text-xs font-semibold text-white hover:bg-brand-blue/90"
                        >
                          Registra notifica
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {notification && (
                  <p className="mt-2 text-xs text-slate-500">
                    Notificato a {notification.recipient} il {formatDateTime(notification.sent_at)}
                  </p>
                )}

                {notifyPhase === deadline.phase && (
                  <form
                    onSubmit={handleRecordNotification}
                    className="mt-3 flex flex-col gap-3 border-t border-slate-100 pt-3 print:hidden"
                  >
                    <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
                      Destinatario
                      <input
                        type="text"
                        value={recipient}
                        onChange={(e) => setRecipient(e.target.value)}
                        className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
                      />
                    </label>
                    <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
                      Contenuto inviato (opzionale)
                      <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        rows={3}
                        className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
                      />
                    </label>
                    <div className="flex gap-3">
                      <button
                        type="submit"
                        disabled={recordMutation.isPending}
                        className="rounded-md bg-brand-blue px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
                      >
                        Conferma
                      </button>
                      <button
                        type="button"
                        onClick={() => setNotifyPhase(null)}
                        className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Annulla
                      </button>
                    </div>
                  </form>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {draft && draftPhase && (
        <section className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 print:hidden">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">
              Bozza email — {NOTIFICATION_PHASE_LABELS[draftPhase] ?? draftPhase}
            </h2>
            <button
              onClick={() => setDraftPhase(null)}
              className="text-sm text-slate-500 hover:underline"
            >
              Chiudi
            </button>
          </div>
          <p className="text-sm font-medium text-slate-700">Oggetto: {draft.subject}</p>
          <pre className="whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm text-slate-700">
            {draft.body}
          </pre>
          <button
            onClick={copyDraft}
            className="w-fit rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
          >
            Copia negli appunti
          </button>
        </section>
      )}
    </div>
  );
}
