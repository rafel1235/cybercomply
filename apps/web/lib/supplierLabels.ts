export const SUPPLIER_CRITICALITY_LABELS: Record<string, string> = {
  alta: "Alta",
  media: "Media",
  bassa: "Bassa",
};

export const SUPPLIER_CRITICALITY_VARIANTS: Record<
  string,
  "success" | "warning" | "danger" | "neutral"
> = {
  alta: "danger",
  media: "warning",
  bassa: "neutral",
};

export const SUPPLIER_STATUS_LABELS: Record<string, string> = {
  conforme: "Conforme",
  parziale: "Parziale",
  non_conforme: "Non conforme",
  non_valutato: "Non valutato",
};

export const SUPPLIER_STATUS_VARIANTS: Record<
  string,
  "success" | "warning" | "danger" | "neutral"
> = {
  conforme: "success",
  parziale: "warning",
  non_conforme: "danger",
  non_valutato: "neutral",
};

/** Domande fisse del questionario di sicurezza fornitori (Guida al Servizio, §4.4),
 * duplicate lato client solo a scopo di etichetta leggibile — il calcolo dello stato
 * resta interamente lato backend (app/services/supplier_scoring.py). */
export const QUESTIONNAIRE_QUESTION_LABELS: Record<string, string> = {
  mfa_attivo: "Autenticazione a più fattori (MFA) attiva sui sistemi critici",
  certificazione_iso27001: "Certificazione ISO 27001 (o equivalente) in corso di validità",
  backup_testato: "Backup regolari con ripristino testato periodicamente",
  incident_response_documentato: "Procedura di incident response documentata",
  formazione_sicurezza_annuale: "Formazione annuale sulla sicurezza per il personale",
};
