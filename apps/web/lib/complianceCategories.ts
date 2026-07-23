/** Raggruppamento in categorie delle 15 misure del catalogo ACN (Det. 164179/2025), usato
 * solo per il filtro nell'interfaccia: è metadato di presentazione, non cambia il backend
 * (che tratta le misure come una lista piatta identificata da `measure_id`). */
export const COMPLIANCE_CATEGORIES: Record<string, string> = {
  valutazione_rischio_annuale: "Rischio e Governance",
  revisione_contratti_fornitori_ict: "Rischio e Governance",
  mfa_accessi_remoti_privilegiati: "Accessi e Identità",
  controllo_accessi_privilegi_minimi: "Accessi e Identità",
  backup_cifrati_testati: "Continuità e Backup",
  piano_business_continuity: "Continuità e Backup",
  piano_disaster_recovery_testato: "Continuità e Backup",
  vulnerability_scanning_periodico: "Sicurezza Tecnica",
  patch_management: "Sicurezza Tecnica",
  segmentazione_rete: "Sicurezza Tecnica",
  crittografia_dati_a_riposo: "Sicurezza Tecnica",
  monitoraggio_log_centralizzato: "Sicurezza Tecnica",
  formazione_personale_annuale: "Persone e Fornitori",
  registro_fornitori_ict_critici: "Persone e Fornitori",
  gestione_incidenti_procedura: "Gestione Incidenti",
};

export const COMPLIANCE_CATEGORY_LIST = Array.from(new Set(Object.values(COMPLIANCE_CATEGORIES)));

export function complianceCategoryOf(measureId: string): string {
  return COMPLIANCE_CATEGORIES[measureId] ?? "Altro";
}

export const MEASURE_STATUS_LABELS: Record<string, string> = {
  conforme: "Conforme",
  parziale: "Parziale",
  non_conforme: "Non conforme",
  non_applicabile: "Non applicabile",
};

export const MEASURE_STATUS_VARIANTS: Record<string, "success" | "warning" | "danger" | "neutral"> = {
  conforme: "success",
  parziale: "warning",
  non_conforme: "danger",
  non_applicabile: "neutral",
};
