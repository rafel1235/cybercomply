/** Metadati dei 4 piani per la UI (etichette, prezzo, elenco funzionalità): rispecchia
 * la tabella autoritativa "NUOVI PIANI.pdf" e `app/services/entitlements.py` nel backend.
 * Nessuna logica di gating qui: i limiti reali restano solo nel backend, questo file
 * serve solo a descrivere i piani nella pagina di confronto. */
import type { Plan, SubscriptionStatus } from "@/lib/queries/billing";

export const PLAN_ORDER: Plan[] = ["free", "essential", "business", "enterprise"];

export const PLAN_LABELS: Record<Plan, string> = {
  free: "Free",
  essential: "Essential",
  business: "Business",
  enterprise: "Enterprise",
};

export const PLAN_PRICE_LABELS: Record<Plan, string> = {
  free: "€0",
  essential: "€99/mese",
  business: "€299/mese",
  enterprise: "da €800/mese",
};

export const PLAN_TAGLINES: Record<Plan, string> = {
  free: "Per farsi un'idea del proprio livello di conformità",
  essential: "Per la maggior parte delle PMI in perimetro NIS2",
  business: "Per aziende con più collaboratori e una filiera di fornitori da monitorare",
  enterprise: "Per gruppi e software house con esigenze di brand e integrazione",
};

export const PLAN_FEATURES: Record<Plan, string[]> = {
  free: [
    "1 utente",
    "3 misure di conformità, in sola lettura",
    "Nessun documento generabile con AI",
    "Incident Reporting non incluso",
    "Supply Chain non incluso",
  ],
  essential: [
    "1 utente",
    "15 misure di conformità, completamente modificabili",
    "5 documenti generati con AI al mese",
    "Incident Reporting incluso",
    "Supply Chain non incluso",
  ],
  business: [
    "Fino a 5 utenti",
    "15 misure di conformità, completamente modificabili",
    "Documenti generati con AI illimitati",
    "Incident Reporting incluso",
    "Supply Chain incluso, fornitori illimitati",
    "Report trimestrali",
  ],
  enterprise: ["Utenti illimitati", "Tutto ciò che include Business", "White-label", "Accesso API"],
};

export const PLAN_PURCHASABLE: Record<Plan, boolean> = {
  free: false,
  essential: true,
  business: true,
  enterprise: false,
};

export const SUBSCRIPTION_STATUS_LABELS: Record<SubscriptionStatus, string> = {
  trialing: "In prova",
  active: "Attivo",
  past_due: "Pagamento non riuscito",
  canceled: "Annullato",
};

export const SUBSCRIPTION_STATUS_VARIANTS: Record<
  SubscriptionStatus,
  "success" | "warning" | "danger" | "neutral" | "info"
> = {
  trialing: "info",
  active: "success",
  past_due: "danger",
  canceled: "neutral",
};
