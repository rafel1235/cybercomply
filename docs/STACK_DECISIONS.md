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

## Modello di prezzo (deciso in Fase 4, per l'implementazione in Fase 6)
Il titolare ha scelto il modello a 4 piani semplici ad abbonamento mensile, senza il doppio
binario Adeguamento una tantum/Mantenimento esplorato in un documento precedente. Fonte
autorevole e definitiva: `NUOVI PIANI.pdf` (Giugno 2026), che sostituisce sia il Business
Plan sia "Piani di Abbonamento.pdf"/"Modello di Ricorrenza.pdf" su questo tema. Nessun
pacchetto con scadenza di accesso a 90/120 giorni: solo abbonamenti ricorrenti, upgrade/
downgrade in qualsiasi momento.

| Caratteristica | Free | Essential | Business | Enterprise |
|---|---|---|---|---|
| Prezzo mensile | €0 | €99 | €299 | da €800 (contratto custom) |
| Assessment | Sì | Sì | Sì | Sì |
| Compliance Tracker | 3 misure, sola lettura | 15 misure, editabile | 15 misure | 15 misure |
| Documenti AI/mese | No (0) | 5 | Illimitati | Illimitati |
| Incident Reporting | No | Sì | Sì | Sì |
| Supply Chain Risk | No | No | Illimitato | Illimitato |
| Utenti | 1 | 1 | 5 | Illimitati |
| Report management | No | No | Trimestrale | Trimestrale + custom |
| Supporto | Nessuno | Email 48h | Email 24h | Account manager dedicato |
| White-label / API | No | No | No | Sì |

Trial: ogni nuovo account può attivare 14 giorni di prova gratuita sul piano Essential
(nessuna carta richiesta); allo scadere, downgrade automatico a Free con i dati esistenti
mantenuti in sola lettura fino a un eventuale upgrade a pagamento.

Il `Plan` enum già presente in `app/models/subscription.py` (free/essential/business/
enterprise) resta coerente e non richiede modifiche strutturali; il `SubscriptionStatus`
enum (trialing/active/past_due/canceled) copre già il ciclo trial→attivo→scaduto. Da
aggiungere in Fase 6: i contatori/limiti d'uso per piano (documenti generati nel mese
corrente, numero utenti, numero fornitori) e il gating dei moduli Incident Reporting/Supply
Chain in base al piano attivo dell'organizzazione — oggi nessuno di questi controlli esiste
nel codice.
