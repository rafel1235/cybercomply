"use client";

import Link from "next/link";
import { ScoreTrendChart } from "@/components/dashboard/ScoreTrendChart";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { auditActionLabel } from "@/lib/auditLabels";
import { formatDateTime, formatRelativeToNow } from "@/lib/format";
import { useLatestAssessment } from "@/lib/queries/assessments";
import { useAuditLog } from "@/lib/queries/auditLog";
import { useComplianceHistory, useComplianceScore } from "@/lib/queries/compliance";

const NIS2_BADGE: Record<string, { label: string; variant: "danger" | "warning" | "neutral" }> = {
  essenziale: { label: "Soggetto essenziale", variant: "danger" },
  importante: { label: "Soggetto importante", variant: "warning" },
  non_in_perimetro: { label: "Fuori perimetro", variant: "neutral" },
};

/** Scadenze regolamentari reali (Guida al Servizio §2.3 e §3.3): non calcolate, elenco
 * statico perché sono date fissate dalla norma, non dipendono dai dati dell'organizzazione. */
const REGULATORY_DEADLINES = [
  {
    date: "2026-09-11",
    label: "CRA: notifica vulnerabilità sfruttate e incidenti gravi (24h/72h)",
    reference: "Reg. UE 2024/2847",
  },
  {
    date: "2026-10-01",
    label: "NIS2: adozione misure tecniche e organizzative",
    reference: "Art. 21 NIS2 + Det. ACN 164179/2025",
  },
  {
    date: "2026-10-01",
    label: "NIS2: nomina responsabile e notifica ad ACN",
    reference: "Art. 23 D.Lgs. 138/2024",
  },
  {
    date: "2026-12-11",
    label: "CRA: punto di contatto per segnalazione vulnerabilità",
    reference: "Reg. UE 2024/2847",
  },
  {
    date: "2026-12-31",
    label: "NIS2: avvio ispezioni e verifiche sistematiche ACN",
    reference: "Art. 32 NIS2",
  },
  {
    date: "2027-12-11",
    label: "CRA: piena applicazione, marcatura CE obbligatoria",
    reference: "Reg. UE 2024/2847",
  },
].filter((d) => new Date(d.date).getTime() >= Date.now() - 1000 * 60 * 60 * 24)
  .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

export default function DashboardPage() {
  const scoreQuery = useComplianceScore();
  const historyQuery = useComplianceHistory();
  const assessmentQuery = useLatestAssessment();
  const auditQuery = useAuditLog(6);

  const visibleAuditEntries = (auditQuery.data ?? []).filter(
    (e) => e.action !== "compliance.score_snapshot"
  );

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-brand-dark">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Indice di conformità */}
        {scoreQuery.isLoading ? (
          <CardSkeleton />
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Indice di conformità</p>
            <p className="text-2xl font-bold text-brand-dark">
              {scoreQuery.data ? `${scoreQuery.data.score_percent}%` : "—"}
            </p>
            <div className="mt-2 h-2 w-full rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-brand-blue transition-all"
                style={{ width: `${scoreQuery.data?.score_percent ?? 0}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {scoreQuery.data
                ? `${scoreQuery.data.measures_conformi}/${scoreQuery.data.measures_total} misure conformi`
                : "Nessun dato"}
            </p>
          </div>
        )}

        {/* Stato NIS2 */}
        {assessmentQuery.isLoading ? (
          <CardSkeleton />
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Stato NIS2</p>
            {assessmentQuery.data ? (
              <div className="mt-2">
                <Badge
                  label={NIS2_BADGE[assessmentQuery.data.nis2_category].label}
                  variant={NIS2_BADGE[assessmentQuery.data.nis2_category].variant}
                />
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-brand-dark">—</p>
                <Link href="/dashboard/assessment" className="mt-1 text-xs text-brand-blue hover:underline">
                  Esegui l&apos;assessment
                </Link>
              </>
            )}
          </div>
        )}

        {/* Stato CRA */}
        {assessmentQuery.isLoading ? (
          <CardSkeleton />
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Stato CRA</p>
            {assessmentQuery.data ? (
              <div className="mt-2">
                <Badge
                  label={assessmentQuery.data.cra_in_scope ? "In perimetro" : "Non in perimetro"}
                  variant={assessmentQuery.data.cra_in_scope ? "warning" : "neutral"}
                />
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-brand-dark">—</p>
                <p className="mt-1 text-xs text-slate-400">Disponibile dopo l&apos;assessment</p>
              </>
            )}
          </div>
        )}

        {/* Prossime scadenze */}
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Prossime scadenze</p>
          <ul className="mt-2 flex flex-col gap-1.5">
            {REGULATORY_DEADLINES.slice(0, 2).map((d) => (
              <li key={d.date + d.label} className="text-xs text-slate-600">
                <span className="font-semibold text-brand-dark">{formatRelativeToNow(d.date)}</span>
                {` — ${d.label}`}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          href="/dashboard/incidents"
          className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
        >
          Apri incidente
        </Link>
        <Link
          href="/dashboard/compliance"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Aggiorna misura
        </Link>
        <Link
          href="/dashboard/compliance?tab=documenti"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Genera documento
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Grafico andamento score */}
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="mb-3 text-sm font-semibold text-slate-700">Andamento indice di conformità</p>
          {historyQuery.isLoading ? (
            <Skeleton className="h-[220px] w-full" />
          ) : (
            <ScoreTrendChart points={historyQuery.data ?? []} />
          )}
        </div>

        {/* Ultime azioni */}
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="mb-3 text-sm font-semibold text-slate-700">Ultime azioni registrate</p>
          {auditQuery.isLoading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-full" />
            </div>
          ) : visibleAuditEntries.length === 0 ? (
            <p className="text-sm text-slate-500">Nessuna azione registrata finora.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {visibleAuditEntries.map((entry) => (
                <li key={entry.id} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700">{auditActionLabel(entry.action)}</span>
                  <span className="text-xs text-slate-400">{formatDateTime(entry.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
