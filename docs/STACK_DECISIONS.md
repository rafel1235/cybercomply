# Scelte di stack — CyberComplyIT

Decisioni prese in Fase 0, come richiesto dalla roadmap tecnica. Ogni scelta riporta la motivazione.

## Frontend: Next.js 14 (App Router) + TypeScript
Confermato dalla roadmap. SSR utile per SEO sulla landing pubblica e per performance percepita
sulla dashboard. App Router per layout annidati (pubblico vs autenticato) e Server Components
dove non serve interattività.

## Backend: Python + FastAPI
Scelto (tra le due opzioni proposte dalla roadmap) per: ecosistema più ricco per prompt
engineering e generazione documenti con Claude API (Fase 5), tipizzazione con Pydantic che
si presta bene a validare payload complessi (assessment, questionari fornitori), ecosistema
maturo per generazione PDF e task asincroni. Prezzo pagato: stack misto (TS frontend +
Python backend) — mitigato condividendo i contratti dati tramite `packages/shared` (tipi
TypeScript) e schemi Pydantic tenuti manualmente allineati, più test di contratto in Fase 3.

## Database: PostgreSQL
Locale in sviluppo (Docker), migrazione a Supabase (eu-central-1, Frankfurt) quando le
credenziali reali saranno disponibili. Scelto per Row Level Security nativa (isolamento dati
per organizzazione, requisito esplicito della Guida al Servizio) e per l'auth integrata.

## ORM: SQLAlchemy 2.0 + Alembic
Coerente con la scelta Python/FastAPI. Alembic per le migration versionate.

## Autenticazione: Supabase Auth
Non costruiamo auth da zero (indicazione esplicita della roadmap). Il frontend usa
`@supabase/supabase-js` per signup/login/reset password; il backend verifica i JWT emessi da
Supabase (HS256, `SUPABASE_JWT_SECRET`) per proteggere le route API e sincronizza l'utente
nelle tabelle applicative (`users`, `organizations`, `organization_members`) al primo accesso.

## Hosting (target, non ancora attivato)
Frontend: Vercel (EU region). Backend: Render EU o Railway EU. Database/Storage: Supabase
(eu-central-1). Nessun account di produzione è stato creato in questa fase: le variabili
d'ambiente usano placeholder in `.env.example`.

## Package manager
pnpm workspaces per la parte JS/TS (`apps/web`, `packages/shared`). Il backend Python usa un
virtualenv/`requirements.txt` separato in `apps/api`, dato che non fa parte dei workspace JS.
