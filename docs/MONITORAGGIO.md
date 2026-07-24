# Monitoraggio produzione (Fase 9)

## Error tracking (Sentry) — implementato nel codice

- **Backend**: `app/core/monitoring.py`, attivato in `app/main.py` all'avvio
  (`configure_sentry`) e usato esplicitamente nell'handler globale delle eccezioni non
  gestite (`capture_exception`, `app/main.py`). Test in `tests/test_monitoring.py`.
- **Frontend**: `instrumentation-client.ts` (browser), `sentry.server.config.ts` (Server
  Components/Route Handler in runtime Node.js), `sentry.edge.config.ts` (middleware,
  runtime Edge), caricati tramite `instrumentation.ts` (hook nativo di Next.js). Il file
  `sentry.client.config.ts` è stato lasciato vuoto (non cancellabile in questa sessione di
  sviluppo per un limite dell'ambiente): l'inizializzazione reale è in
  `instrumentation-client.ts`, la convenzione corrente raccomandata dall'SDK.
- **`next.config.js`**: `withSentryConfig` viene applicato solo se
  `NEXT_PUBLIC_SENTRY_DSN` è impostato — altrimenti la build resta quella semplice,
  invariata, senza il costo di build aggiuntivo che l'instrumentazione comporta.
  L'upload dei source map (rende leggibili gli stack trace del codice minificato) è
  condizionato separatamente a `SENTRY_AUTH_TOKEN`.

**Cosa manca (richiede un account reale)**: nessun progetto Sentry è mai stato creato in
questa sessione di sviluppo, quindi nessuna delle due integrazioni è mai stata testata
contro un vero endpoint Sentry (solo con DSN sintatticamente validi ma finti, per
verificare che l'inizializzazione non sollevi eccezioni — vedi `tests/test_monitoring.py`).

### Attivazione (quando pronti)
1. Creare un progetto su [sentry.io](https://sentry.io) (piano gratuito sufficiente
   all'inizio, come indicato dalla roadmap) — uno per il backend (piattaforma Python) e
   uno per il frontend (piattaforma Next.js), oppure un unico progetto Next.js se si
   preferisce un solo DSN (Sentry supporta entrambi gli approcci).
2. Impostare `SENTRY_DSN` nelle variabili d'ambiente Render (backend) e
   `NEXT_PUBLIC_SENTRY_DSN` in Vercel (frontend, scope Preview e Production).
3. Configurare in Sentry un alert email per ogni nuovo errore (Settings → Alerts →
   "Send a notification for new issues"), come richiesto dalla roadmap.
4. Facoltativo: `SENTRY_AUTH_TOKEN` + `SENTRY_ORG` + `SENTRY_PROJECT` in Vercel per
   l'upload dei source map.

## Uptime monitoring — da configurare (nessun codice necessario)

La roadmap suggerisce Better Uptime o UptimeRobot (entrambi con piano gratuito). Nessuno
dei due richiede integrazione nel codice: si configura un monitor HTTP puntato su
`https://cybercomplyit.it` (frontend) e su
`https://api.cybercomplyit.it/api/v1/health` o l'equivalente URL Render del backend
(l'endpoint `GET /health` esiste già dalla Fase 3, pensato esattamente per questo), con
alert email/SMS se il sito risulta irraggiungibile.

## Metriche backend (response time, error rate, CPU/RAM)

Render fornisce queste metriche nativamente nella dashboard di ogni servizio (piano
Starter incluso), senza bisogno di codice aggiuntivo. Per l'alert "response time > 2
secondi" richiesto dalla roadmap: da configurare nella sezione Alerts della dashboard
Render una volta che il servizio è stato creato (non disponibile in questa sessione di
sviluppo, nessun servizio Render reale esiste ancora).

## Spesa Anthropic API

Anthropic fornisce un dashboard di utilizzo e la possibilità di impostare un budget alert
direttamente nella console (console.anthropic.com → Settings → Billing). Non è stato
costruito un sistema di monitoraggio spesa separato in questa piattaforma: l'audit log
registra già token e costo stimato per ogni chiamata AI (Fase 5,
`app/services/ai_client.py`), che resta la fonte per un'eventuale dashboard interna
futura, ma per ora il controllo budget mensile è affidato al pannello nativo di
Anthropic, più immediato da attivare (nessuno sviluppo necessario).
