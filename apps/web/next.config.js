/** @type {import('next').NextConfig} */

// CSP costruita dagli stessi URL usati a runtime (Supabase, backend API), non hardcoded:
// una CSP statica che non includesse questi origin bloccherebbe login e chiamate API.
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, "");

// Fase 8 (roadmap): CSP stretta. `unsafe-inline` su script-src resta necessario perché
// Next.js (App Router, senza setup di nonce dedicato) inietta script di bootstrap
// inline: rimuoverlo richiederebbe una CSP basata su nonce generati per richiesta in
// middleware.ts, non ancora fatto — annotato come possibile indurimento ulteriore.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  `connect-src 'self' ${SUPABASE_URL} ${API_ORIGIN}`.trim(),
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig = {
  reactStrictMode: true,
  // Non esporre la versione di Next.js nell'header X-Powered-By (Fase 8: "non esporre
  // versioni di librerie negli header HTTP").
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Content-Security-Policy", value: CSP },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
};

// Fase 9: withSentryConfig strumenta il bundle (client instrumentation, tag di release,
// e opzionalmente l'upload dei source map) e ha un costo di build non trascurabile — ha
// senso pagarlo solo quando Sentry è davvero in uso. Si attiva quando è presente un DSN
// pubblico reale (NEXT_PUBLIC_SENTRY_DSN): mai configurato in questa sessione di
// sviluppo, nessun progetto Sentry reale creato, quindi la build usa qui la
// configurazione semplice, invariata. L'upload dei source map (che richiede una vera
// chiamata di rete verso l'API di Sentry) è a sua volta condizionato separatamente alla
// presenza di SENTRY_AUTH_TOKEN, un segreto diverso e più sensibile del DSN pubblico.
const sentryEnabled = Boolean(process.env.NEXT_PUBLIC_SENTRY_DSN);

if (!sentryEnabled) {
  module.exports = nextConfig;
} else {
  const { withSentryConfig } = require("@sentry/nextjs");

  module.exports = withSentryConfig(nextConfig, {
    silent: true,
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    widenClientFileUpload: true,
    // Nessuna route intercettata per il tunneling degli eventi Sentry (evita di
    // introdurre un endpoint aggiuntivo non richiesto dalla roadmap); i browser con
    // ad-blocker potrebbero bloccare le chiamate dirette a Sentry, compromesso
    // accettabile per questa fase.
    telemetry: false,
    sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
  });
}
