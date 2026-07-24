// Hook di instrumentation di Next.js (App Router): carica la configurazione Sentry
// corretta in base al runtime in cui il codice server sta effettivamente girando.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}
