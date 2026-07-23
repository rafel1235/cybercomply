/** Etichette leggibili per le azioni dell'audit log, mostrate nella dashboard e nello
 * storico. `compliance.score_snapshot` è volutamente escluso altrove: è un evento tecnico
 * interno (usato per ricostruire lo storico del punteggio), non un'azione dell'utente. */
export const AUDIT_ACTION_LABELS: Record<string, string> = {
  "organization.updated": "Dati organizzazione aggiornati",
  "organization.member_removed": "Membro rimosso dal team",
  "organization.member_invited": "Nuovo invito al team inviato",
  "document.generated": "Documento generato",
  "document.updated": "Documento modificato",
  "document.deleted": "Documento eliminato",
  "incident.created": "Incidente aperto",
  "incident.closed": "Incidente chiuso",
  "incident.notification_recorded": "Notifica incidente registrata",
  "supplier.created": "Fornitore aggiunto al registro",
  "supplier.deleted": "Fornitore rimosso dal registro",
  "supplier.questionnaire_sent": "Questionario fornitore inviato",
  "compliance.measure_updated": "Misura di conformità aggiornata",
};

export function auditActionLabel(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? action;
}
