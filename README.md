# CyberComplyIT — Monorepo

Piattaforma SaaS italiana di cyber-compliance per PMI (NIS2, Cyber Resilience Act,
D.Lgs. 138/2024). Questo repository segue la Roadmap Tecnica interna, fase per fase.

Stato di avanzamento: **Fase 0 → Fase 10 completate e verificate** (setup, autenticazione,
modello dati, API completa, frontend dei 4 moduli, generazione documenti con AI, pagamenti
Stripe, email transazionali, sicurezza/GDPR, infrastruttura e deploy, performance e
accessibilità) — vedi `docs/ROADMAP_PROGRESS.md` per il dettaglio di cosa è stato fatto e
come è stato verificato in ciascuna fase. La **Fase 11 (Preparazione al lancio)** non è
ancora iniziata: contenuti legali definitivi con un avvocato, onboarding guidato, test
end-to-end con Playwright, penetration test e load test restano da fare prima del lancio
commerciale.

## Struttura

```
/apps
  /web     → frontend Next.js 14 + TypeScript + Tailwind CSS
  /api     → backend FastAPI + SQLAlchemy + Alembic
/packages
  /shared  → tipi TypeScript condivisi tra frontend e (dove serve) documentazione contratti API
/infra     → configurazione cloud/CI (policy RLS Supabase, script di deploy)
/docs      → documentazione interna (scelte di stack, avanzamento roadmap, runbook operativi)
```

Perché queste scelte: vedi `docs/STACK_DECISIONS.md`. Nessuna libreria di componenti UI
(es. shadcn/ui) è installata: i componenti sono scritti a mano con Tailwind, vedi
`apps/web/components/ui/`.

## Documentazione operativa

- `docs/STACK_DECISIONS.md` — motivazione delle scelte tecnologiche
- `docs/ROADMAP_PROGRESS.md` — cosa è stato fatto in ogni fase e come è stato verificato
- `docs/AMBIENTI.md` — ambienti dev/staging/produzione e checklist di configurazione one-time
- `docs/MONITORAGGIO.md` — Sentry, uptime monitoring, alerting
- `docs/DISASTER_RECOVERY.md` — backup e procedura di ripristino
- `docs/PERFORMANCE.md` — paginazione, indici, ottimizzazioni frontend
- `docs/ACCESSIBILITA.md` — verifica WCAG AA
- `docs/REGISTRO_TRATTAMENTI.md` — Registro delle Attività di Trattamento (Art. 30 GDPR)

## Setup rapido (sviluppo locale)

Prerequisiti: Node.js 20+, pnpm 9+, Python 3.11+.

Docker è utile solo per far girare un Postgres locale per lo **sviluppo** (vedi sotto): i
**test** del backend non richiedono Docker né alcun Postgres esterno, perché avviano da
soli un Postgres incorporato isolato tramite `pgserver` (vedi `apps/api/tests/conftest.py`)
e non toccano mai `DATABASE_URL`.

### 1. Database locale (solo per far girare il server in sviluppo, non per i test)

```bash
docker run --name cybercomplyit-db -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=cybercomplyit -p 5432:5432 -d postgres:16
```

In alternativa puoi puntare `DATABASE_URL` direttamente a un progetto Supabase reale.

### 2. Backend (apps/api)

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # compila i valori reali quando li avrai (Supabase, Anthropic, Stripe, Resend, Sentry...)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API disponibile su http://localhost:8000 — documentazione automatica su
http://localhost:8000/docs

### 3. Frontend (apps/web)

```bash
cd apps/web
pnpm install
cp .env.example .env.local   # compila i valori reali (Supabase URL/anon key, API base URL, Sentry)
pnpm dev
```

Frontend disponibile su http://localhost:3000

## Dati di sviluppo (seed) e backup

Dopo aver applicato le migration, puoi popolare il database locale con dati fittizi ma
realistici (3 aziende con profili NIS2 diversi, utenti, assessment, misure di conformità,
documenti, un incidente, fornitori, abbonamento):

```bash
cd apps/api
python -m scripts.seed_dev_data
```

Per un backup manuale del database (oltre a quelli automatici già inclusi da Supabase in
produzione, vedi `docs/DISASTER_RECOVERY.md`):

```bash
DATABASE_URL="postgresql://..." ./scripts/backup_db.sh
```

## Row Level Security (Supabase)

`infra/supabase/rls_policies.sql` contiene le policy RLS che isolano i dati per
organizzazione. Vanno eseguite una volta, dopo le migration, dallo SQL Editor del tuo
progetto Supabase reale (richiedono la funzione `auth.uid()`, non disponibile su un
Postgres locale generico).

## Variabili d'ambiente richieste

Vedi `apps/api/.env.example` e `apps/web/.env.example`. Nessun segreto è presente nel
repository: tutte le chiavi sono placeholder finché non vengono fornite dal titolare del
progetto. Integrazioni configurabili (ognuna con degradazione controllata se assente —
l'app resta funzionante, disabilita solo la singola funzionalità collegata):

- **Supabase** — autenticazione, database, storage PDF (`SUPABASE_URL`,
  `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`,
  `SUPABASE_STORAGE_BUCKET`)
- **Anthropic (Claude)** — generazione AI dei 9 documenti di conformità
  (`ANTHROPIC_API_KEY`)
- **Stripe** — pagamenti e piani (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`,
  `STRIPE_WEBHOOK_SECRET`, price ID per Essential/Business)
- **Resend** — email transazionali (`RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`)
- **Sentry** — error tracking backend e frontend (`SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN`)
- **FIELD_ENCRYPTION_KEY** — cifratura a riposo di P.IVA e dati incidenti (Fase 8):
  obbligatoria, non degradabile, senza non parte l'app

## Cosa serve dal titolare (non automatizzabile da qui)

- Creare un progetto Supabase reale (URL, anon key, service role key, JWT secret, bucket
  storage) — necessario per login/registrazione e generazione PDF con dati reali oltre ai
  test locali.
- Account Anthropic con API key per la generazione documenti.
- Account Stripe in modalità live, dominio `cybercomplyit.it` con DNS configurato
  (SPF/DKIM/DMARC per Resend), progetto Sentry.
- P.IVA e dati societari reali per il footer del sito (vedi
  `apps/web/components/marketing/Footer.tsx`, attualmente un placeholder).
- Revisione legale di Termini di Servizio e Privacy Policy con un avvocato (bozze
  tecniche onesto-non-template già presenti in `apps/web/app/(public)/privacy-policy` e
  `apps/web/app/(public)/termini-di-servizio`, ma non sostituiscono un testo legale
  definitivo — Fase 11).
- Configurazione one-time GitHub (secret di deploy, branch protection, ambiente
  `production` con reviewer obbligatorio) e Render/Vercel — vedi `docs/AMBIENTI.md`.

## Test

```bash
# Backend (nessun Postgres esterno richiesto: pgserver incorporato nei test)
cd apps/api && pytest --cov=app

# Frontend
cd apps/web && pnpm exec tsc --noEmit && pnpm lint && pnpm build
```

## CI/CD

`.github/workflows/ci.yml` esegue, su ogni push/PR: scansione automatica dei secret
(gitleaks), lint + test del backend (ruff, black, pytest con copertura), lint + build del
frontend (tsc, next lint, next build). Sui push su `main`, dopo che tutti i controlli sono
passati, esegue il deploy automatico su staging e poi (dietro approvazione manuale
obbligatoria da GitHub Environment) su produzione. Il deploy del frontend su Vercel è
gestito nativamente da Vercel stesso una volta collegato il repository. Vedi
`docs/AMBIENTI.md` per la checklist di configurazione one-time dei secret e degli ambienti
GitHub.
