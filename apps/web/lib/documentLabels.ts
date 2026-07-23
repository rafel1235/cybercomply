/** Etichette leggibili per i 9 tipi di documento generabili (Guida al Servizio §4.3). */
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  registro_rischi: "Registro dei Rischi",
  procedura_incident_response: "Procedura Incident Response",
  piano_bcp: "Piano di Business Continuity (BCP)",
  politica_supply_chain: "Politica Supply Chain",
  politica_crittografia: "Politica di Crittografia",
  politica_controllo_accessi: "Politica di Controllo Accessi",
  procedura_vulnerability_disclosure: "Procedura Vulnerability Disclosure",
  piano_formazione: "Piano di Formazione",
  registro_asset_critici: "Registro Asset Critici",
};

export const DOCUMENT_TYPES = Object.keys(DOCUMENT_TYPE_LABELS);

export function documentTypeLabel(docType: string): string {
  return DOCUMENT_TYPE_LABELS[docType] ?? docType;
}
