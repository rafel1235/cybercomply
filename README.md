# CyberComplyIT — Monorepo

Piattaforma SaaS italiana di cyber-compliance per PMI (NIS2, Cyber Resilience Act,
D.Lgs. 138/2024). Questo repository segue la Roadmap Tecnica interna, fase per fase.

Stato di avanzamento: **Fase 0 (Setup) + Fase 1 (Autenticazione) + Fase 2 (Modello dati
completo) + Fase 3 (API completa: organizzazione, assessment, compliance, documenti,
incidenti, fornitori)** — vedi `docs/ROADMAP_PROGRESS.md`.

## Struttura

```
/apps
  /web     → frontend Next.js 14 + TypeScript + Tailwind + shadcn/ui
  /api     → backend FastAPI + SQLAlchemy + Alembic
/packages
  /shared  → tipi TypeScript condivisi tra frontend e (dove serve) documentazione contratti API
/infra     → configurazione cloud/CI (placeholder, popolato in Fase 9)
/docs      → documentazione interna (scelte di stack, avanzamento roadmap)
```

Perché queste scelte: vedi `docs/STACK_DECISIONS.md`.

## Setup rapido (sviluppo locale)

Prerequisiti: Node.js 20+, pnpm 9+, Python 3.11+, Docker (per Postgres locale).

### 1. Database locale

```bash
docker run --name cybercomplyit-db -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=cybercomplyit -p 5432:5432 -d postgres:16
```

### 2. Backend (apps/api)

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # compila i valori reali quando li avrai (Supabase, Anthropic...)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API disponibile su http://localhost:8000 — documentazione automatica su
http://localhost:8000/docs

### 3. Frontend (apps/web)

```bash
cd apps/web
pnpm install
cp .env.example .env.local   # compila i valori reali (Supabase URL/anon key, API base URL)
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
produzione):

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
repository: tutte le chiavi (Supabase, Anthropic, Stripe, Resend) sono placeholder finché non
verranno fornite dal titolare del progetto.

## Cosa serve dal titolare (non automatizzabile da qui)

- Creare un progetto Supabase reale (URL, anon key, service role key, JWT secret) — necessario
  per far funzionare login/registrazione con dati reali oltre ai test locali.
- Account Anthropic con API key per la generazione documenti (Fase 5, non ancora iniziata).
- Account Stripe, dominio `cybercomplyit.it`, provider email transazionale (Fase 6-7).
- Revisione legale di Termini di Servizio/Privacy Policy con un avvocato (Fase 11).

## Test

```bash
# Backend
cd apps/api && pytest

# Frontend (lint)
cd apps/web && pnpm lint
```

## CI

`.github/workflows/ci.yml` esegue lint + test su ogni push/PR (backend e frontend). Deploy
automatico non è ancora configurato (arriva in Fase 9, richiede hosting reale).
