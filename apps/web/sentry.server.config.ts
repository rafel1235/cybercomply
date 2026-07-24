// Error tracking lato server (Server Components, Route Handlers, middleware in runtime
// Node.js). Vedi sentry.client.config.ts per la nota sulla degradazione controllata: senza
// SENTRY_DSN configurato, questa inizializzazione è un no-op innocuo.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
  tracesSampleRate: process.env.NEXT_PUBLIC_ENVIRONMENT === "production" ? 0.1 : 1.0,
  sendDefaultPii: false,
});
