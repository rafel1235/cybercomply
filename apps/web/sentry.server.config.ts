// Error tracking lato server (Server Components, Route Handlers, middleware in runtime
// Node.js). Vedi instrumentation-client.ts per la nota sulla degradazione controllata:
// senza un DSN configurato, questa inizializzazione è un no-op innocuo.
//
// Bug reale corretto (Fase 10 — audit finale): usava solo `SENTRY_DSN`, una variabile mai
// presente in `.env.example` e senza alcun fallback — impostare solo
// `NEXT_PUBLIC_SENTRY_DSN` (come documentato in .env.example) avrebbe lasciato il
// tracking server-side permanentemente disattivato anche a produzione configurata. Un DSN
// Sentry non è un segreto (è pensato per essere incluso nel bundle client, da cui il
// prefisso NEXT_PUBLIC_), quindi riusarlo lato server è la soluzione corretta: `SENTRY_DSN`
// resta disponibile per chi preferisce un progetto Sentry separato per server/client.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
  tracesSampleRate: process.env.NEXT_PUBLIC_ENVIRONMENT === "production" ? 0.1 : 1.0,
  sendDefaultPii: false,
});
