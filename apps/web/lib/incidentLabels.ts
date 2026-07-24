export const INCIDENT_STATUS_LABELS: Record<string, string> = {
  aperto: "Aperto",
  in_gestione: "In gestione",
  chiuso: "Chiuso",
};

export const INCIDENT_STATUS_VARIANTS: Record<
  string,
  "success" | "warning" | "danger" | "neutral"
> = {
  aperto: "danger",
  in_gestione: "warning",
  chiuso: "success",
};

/** Le 5 fasi di notifica (3 NIS2 + 2 CRA verso ENISA), con etichetta e destinatario di
 * default coerenti con la Guida al Servizio (§2.3/§3.3). */
export const NOTIFICATION_PHASE_LABELS: Record<string, string> = {
  early_warning_24h: "Early warning (24h)",
  notifica_72h: "Notifica completa (72h)",
  relazione_30gg: "Relazione finale (30gg)",
  cra_enisa_24h: "CRA — notifica ENISA (24h)",
  cra_enisa_72h: "CRA — notifica ENISA completa (72h)",
};

export const NOTIFICATION_PHASE_DEFAULT_RECIPIENT: Record<string, string> = {
  early_warning_24h: "CSIRT Italia",
  notifica_72h: "CSIRT Italia",
  relazione_30gg: "CSIRT Italia",
  cra_enisa_24h: "ENISA",
  cra_enisa_72h: "ENISA",
};
