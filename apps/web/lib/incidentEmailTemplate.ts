import { formatDateTime } from "@/lib/format";
import { NOTIFICATION_PHASE_LABELS } from "@/lib/incidentLabels";
import type { Incident } from "@/lib/queries/incidents";

/**
 * Genera la bozza di email di notifica per una fase (CSIRT Italia o ENISA), a partire dai
 * dati reali dell'incidente. Resta una bozza da rivedere e completare manualmente prima
 * dell'invio: non sostituisce la valutazione legale del caso specifico.
 */
export function buildNotificationEmailDraft(
  incident: Incident,
  phase: string
): { subject: string; body: string } {
  const phaseLabel = NOTIFICATION_PHASE_LABELS[phase] ?? phase;
  const isEnisa = phase.startsWith("cra_enisa");
  const authority = isEnisa ? "ENISA" : "CSIRT Italia";
  const description =
    typeof incident.data?.descrizione === "string"
      ? incident.data.descrizione
      : "[Descrivere qui la natura dell'incidente]";

  const subject = `Notifica incidente ${incident.reference_code} — ${phaseLabel}`;

  const body = `A: ${authority}
Oggetto: ${subject}

Con la presente si notifica, ai sensi della normativa applicabile (${
    isEnisa ? "Cyber Resilience Act, Regolamento UE 2024/2847" : "NIS2, Art. 23 D.Lgs. 138/2024"
  }), il seguente incidente di sicurezza:

Riferimento interno: ${incident.reference_code}
Tipologia: ${incident.incident_type}
Data/ora apertura: ${formatDateTime(incident.opened_at)}
Fase di notifica: ${phaseLabel}

Descrizione dell'incidente:
${description}

Impatto e sistemi coinvolti:
[Da completare]

Misure di contenimento adottate:
[Da completare]

Referente per eventuali chiarimenti:
[Nome, ruolo, contatto]

Distinti saluti.`;

  return { subject, body };
}
