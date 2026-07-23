"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  COMPLIANCE_CATEGORY_LIST,
  MEASURE_STATUS_LABELS,
  MEASURE_STATUS_VARIANTS,
  complianceCategoryOf,
} from "@/lib/complianceCategories";
import { DOCUMENT_TYPES, documentTypeLabel } from "@/lib/documentLabels";
import { formatDateTime } from "@/lib/format";
import { useAuditLog } from "@/lib/queries/auditLog";
import {
  useComplianceMeasures,
  useComplianceScore,
  useUpdateComplianceMeasure,
} from "@/lib/queries/compliance";
import {
  useDeleteDocument,
  useDocuments,
  useDownloadDocumentPdf,
  useGenerateDocument,
  useGenerateDocumentPdf,
} from "@/lib/queries/documents";
import { useToast } from "@/lib/toast";

export default function CompliancePage() {
  const router = useRouter();
  const [tab, setTab] = useState<"misure" | "documenti">("misure");

  // Legge il parametro ?tab= solo lato client (dopo il mount): evita di dover avvolgere
  // la pagina in un Suspense boundary solo per leggere un parametro non essenziale al
  // primo render (usato dalla quick action "Genera documento" della dashboard).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("tab") === "documenti") {
      setTab("documenti");
    }
  }, []);

  function switchTab(next: "misure" | "documenti") {
    setTab(next);
    router.replace(`/dashboard/compliance?tab=${next}`, { scroll: false });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-brand-dark">Compliance Tracker</h1>
        <Link
          href="/dashboard/compliance/report"
          target="_blank"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Esporta report conformità (PDF)
        </Link>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        <button
          onClick={() => switchTab("misure")}
          className={`border-b-2 px-3 py-2 text-sm font-medium ${
            tab === "misure" ? "border-brand-blue text-brand-blue" : "border-transparent text-slate-500"
          }`}
        >
          Misure
        </button>
        <button
          onClick={() => switchTab("documenti")}
          className={`border-b-2 px-3 py-2 text-sm font-medium ${
            tab === "documenti" ? "border-brand-blue text-brand-blue" : "border-transparent text-slate-500"
          }`}
        >
          Documenti
        </button>
      </div>

      {tab === "misure" ? <MeasuresTab /> : <DocumentsTab />}
    </div>
  );
}

function MeasuresTab() {
  const measuresQuery = useComplianceMeasures();
  const scoreQuery = useComplianceScore();
  const updateMutation = useUpdateComplianceMeasure();
  const auditQuery = useAuditLog(100);
  const { showToast } = useToast();

  const [categoryFilter, setCategoryFilter] = useState("Tutte");
  const [statusFilter, setStatusFilter] = useState("Tutti");
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string | undefined>>({});
  const [historyOpenFor, setHistoryOpenFor] = useState<string | null>(null);

  const measures = measuresQuery.data ?? [];
  const filtered = measures.filter((m) => {
    const matchesCategory = categoryFilter === "Tutte" || complianceCategoryOf(m.measure_id) === categoryFilter;
    const matchesStatus = statusFilter === "Tutti" || m.status === statusFilter;
    return matchesCategory && matchesStatus;
  });

  async function handleStatusChange(measureId: string, status: string, note: string | null) {
    try {
      await updateMutation.mutateAsync({ measureId, status, note });
      showToast("Misura aggiornata.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'aggiornamento", "error");
    }
  }

  async function handleNoteSave(measureId: string, status: string) {
    const note = noteDrafts[measureId];
    if (note === undefined) return;
    try {
      await updateMutation.mutateAsync({ measureId, status, note });
      showToast("Nota salvata.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante il salvataggio della nota", "error");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {scoreQuery.data && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Punteggio attuale</p>
          <p className="text-2xl font-bold text-brand-dark">{scoreQuery.data.score_percent}%</p>
          <p className="text-xs text-slate-400">
            {scoreQuery.data.measures_conformi} conformi · {scoreQuery.data.measures_parziali} parziali ·{" "}
            {scoreQuery.data.measures_non_conformi} non conformi ·{" "}
            {scoreQuery.data.measures_non_applicabili} non applicabili
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="Tutte">Tutte le categorie</option>
          {COMPLIANCE_CATEGORY_LIST.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="Tutti">Tutti gli stati</option>
          {Object.entries(MEASURE_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {measuresQuery.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : filtered.length === 0 ? (
        <EmptyState title="Nessuna misura corrisponde ai filtri selezionati" />
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((m) => (
            <div key={m.measure_id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-800">{m.label}</p>
                  <p className="text-xs text-slate-400">
                    {complianceCategoryOf(m.measure_id)} · {m.normative_reference}
                  </p>
                </div>
                <Badge label={MEASURE_STATUS_LABELS[m.status]} variant={MEASURE_STATUS_VARIANTS[m.status]} />
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <select
                  value={m.status}
                  onChange={(e) => handleStatusChange(m.measure_id, e.target.value, m.note)}
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                >
                  {Object.entries(MEASURE_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-400">
                  Ultimo aggiornamento: {formatDateTime(m.updated_at)}
                </p>
                <button
                  type="button"
                  onClick={() => setHistoryOpenFor(historyOpenFor === m.measure_id ? null : m.measure_id)}
                  className="text-xs font-medium text-brand-blue hover:underline"
                >
                  {historyOpenFor === m.measure_id ? "Nascondi cronologia" : "Cronologia"}
                </button>
              </div>

              <textarea
                placeholder='Note (es. "abbiamo il MFA attivo su Office 365 dal...")'
                value={noteDrafts[m.measure_id] ?? m.note ?? ""}
                onChange={(e) =>
                  setNoteDrafts((prev) => ({ ...prev, [m.measure_id]: e.target.value }))
                }
                onBlur={() => handleNoteSave(m.measure_id, m.status)}
                rows={2}
                className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
              />

              {historyOpenFor === m.measure_id && (
                <div className="mt-3 border-t border-slate-100 pt-3">
                  {(() => {
                    const entries = (auditQuery.data ?? []).filter(
                      (e) => e.action === "compliance.measure_updated" && e.details.measure_id === m.measure_id
                    );
                    if (entries.length === 0) {
                      return <p className="text-xs text-slate-400">Nessuna modifica registrata.</p>;
                    }
                    return (
                      <ul className="flex flex-col gap-1">
                        {entries.map((e) => (
                          <li key={e.id} className="text-xs text-slate-500">
                            {formatDateTime(e.created_at)} — stato impostato a{" "}
                            {MEASURE_STATUS_LABELS[String(e.details.status)] ?? String(e.details.status)}
                          </li>
                        ))}
                      </ul>
                    );
                  })()}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DocumentsTab() {
  const documentsQuery = useDocuments();
  const generateMutation = useGenerateDocument();
  const generatePdfMutation = useGenerateDocumentPdf();
  const downloadMutation = useDownloadDocumentPdf();
  const deleteMutation = useDeleteDocument();
  const { showToast } = useToast();

  const [selectedType, setSelectedType] = useState(DOCUMENT_TYPES[0]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const documents = documentsQuery.data ?? [];
  // Solo l'ultima versione per tipo, per non affollare la vista principale: lo storico
  // completo resta comunque accessibile via API (GET /documents?doc_type=...).
  const latestByType = new Map<string, (typeof documents)[number]>();
  for (const doc of documents) {
    const existing = latestByType.get(doc.doc_type);
    if (!existing || doc.version > existing.version) {
      latestByType.set(doc.doc_type, doc);
    }
  }

  async function handleGenerate() {
    try {
      await generateMutation.mutateAsync(selectedType);
      showToast(`${documentTypeLabel(selectedType)} generato.`, "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante la generazione", "error");
    }
  }

  async function handleGeneratePdf(documentId: string) {
    try {
      await generatePdfMutation.mutateAsync(documentId);
      showToast("PDF generato, pronto per il download.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante la generazione del PDF", "error");
    }
  }

  async function handleDownload(documentId: string, docType: string, version: number) {
    try {
      await downloadMutation.mutateAsync({
        documentId,
        fileName: `${docType}_v${version}.pdf`,
      });
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante il download", "error");
    }
  }

  async function handleDelete(documentId: string) {
    try {
      await deleteMutation.mutateAsync(documentId);
      showToast("Documento eliminato.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'eliminazione", "error");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          {DOCUMENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {documentTypeLabel(t)}
            </option>
          ))}
        </select>
        <button
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
          className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
        >
          {generateMutation.isPending ? "Generazione…" : "Genera documento"}
        </button>
      </div>

      {documentsQuery.isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : latestByType.size === 0 ? (
        <EmptyState
          title="Nessun documento generato finora"
          description="Scegli un tipo di documento sopra e genera la prima versione."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {Array.from(latestByType.values()).map((doc) => (
            <div key={doc.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-800">{documentTypeLabel(doc.doc_type)}</p>
                    {doc.content.generato_da === "ai" ? (
                      <Badge label="Generato con AI" variant="info" />
                    ) : (
                      <Badge label="Segnaposto" variant="neutral" />
                    )}
                  </div>
                  <p className="text-xs text-slate-400">
                    Versione {doc.version} · generato il {formatDateTime(doc.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setExpandedId(expandedId === doc.id ? null : doc.id)}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {expandedId === doc.id ? "Nascondi anteprima" : "Anteprima"}
                  </button>
                  {doc.pdf_url ? (
                    <button
                      onClick={() => handleDownload(doc.id, doc.doc_type, doc.version)}
                      disabled={downloadMutation.isPending}
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                    >
                      Scarica PDF
                    </button>
                  ) : (
                    <button
                      onClick={() => handleGeneratePdf(doc.id)}
                      disabled={generatePdfMutation.isPending}
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                    >
                      {generatePdfMutation.isPending ? "Generazione PDF…" : "Genera PDF"}
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    Elimina
                  </button>
                </div>
              </div>

              {expandedId === doc.id && (
                <div className="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-4">
                  {doc.content.disclaimer && (
                    <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-800">
                      {doc.content.disclaimer}
                    </p>
                  )}
                  {doc.content.sezioni.map((section, i) => (
                    <div key={i}>
                      <p className="text-sm font-semibold text-slate-700">{section.titolo}</p>
                      <p className="text-sm text-slate-600">{section.corpo}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
