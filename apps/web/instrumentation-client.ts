// Error tracking lato browser (Fase 9 — roadmap tecnica: monitoraggio produzione).
// Convenzione Next.js/Sentry corrente per il codice di inizializzazione lato client
// (sostituisce il precedente sentry.client.config.ts, deprecato e incompatibile con
// Turbopack).
//
// Stesso principio di degradazione controllata usato per ogni integrazione esterna di
// questa piattaforma: se NEXT_PUBLIC_SENTRY_DSN non è impostato (mai successo in questa
// sessione di sviluppo, nessun progetto Sentry reale creato), Sentry.init con un DSN
// vuoto/undefined non fa nulla — nessun errore, nessuna chiamata di rete, comportamento
// nativo dell'SDK.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
  tracesSampleRate: process.env.NEXT_PUBLIC_ENVIRONMENT === "production" ? 0.1 : 1.0,
  // GDPR (Fase 8): non registrare replay di sessione per default — è un'opzione di
  // Sentry potenzialmente molto invasiva (registra le interazioni dell'utente), da
  // attivare solo dopo un'attenta valutazione privacy, non come impostazione di default.
  sendDefaultPii: false,
});

// Richiesto dall'SDK per tracciare le navigazioni client-side dell'App Router come
// transazioni di performance (senza questo hook, ogni navigazione risulterebbe come una
// singola pagina invece che come cambio di rotta tracciato).
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
