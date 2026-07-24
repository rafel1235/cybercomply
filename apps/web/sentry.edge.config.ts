// Error tracking per il runtime Edge (middleware.ts gira in Edge Runtime in questo
// progetto). Vedi sentry.client.config.ts per la nota sulla degradazione controllata.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
  tracesSampleRate: process.env.NEXT_PUBLIC_ENVIRONMENT === "production" ? 0.1 : 1.0,
  sendDefaultPii: false,
});
