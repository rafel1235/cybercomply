// Error tracking per il runtime Edge (middleware.ts gira in Edge Runtime in questo
// progetto). Vedi sentry.server.config.ts per la nota sul fallback del DSN (bug reale
// corretto in Fase 10: senza, questo restava disattivato con solo NEXT_PUBLIC_SENTRY_DSN
// impostato, come documentato in .env.example).
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
  tracesSampleRate: process.env.NEXT_PUBLIC_ENVIRONMENT === "production" ? 0.1 : 1.0,
  sendDefaultPii: false,
});
