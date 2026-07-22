# Avanzamento Roadmap Tecnica

Aggiornato automaticamente ad ogni modulo consegnato. Le fasi seguono la numerazione della
Roadmap Tecnica CyberComplyIT.

## Fase 0 — Setup iniziale — ✅ completata (parti eseguibili da qui)
- [x] Struttura monorepo (`/apps/web`, `/apps/api`, `/packages/shared`, `/infra`, `/docs`)
- [x] `.gitignore` corretto (no `.env`, no `node_modules`, no `.venv`)
- [x] ESLint + Prettier (frontend), Ruff + Black (backend)
- [x] Package manager: pnpm workspaces (JS/TS) + venv/requirements (Python)
- [x] README con istruzioni di setup
- [x] Scelte di stack documentate con motivazione (`docs/STACK_DECISIONS.md`)
- [x] Repository Git locale inizializzato con commit iniziale
- [ ] Push su repository GitHub privato reale — **richiede account GitHub del titolare**

## Fase 1 — Autenticazione e gestione account — ✅ completata (parti eseguibili da qui)
- [x] Integrazione Supabase Auth (client frontend + verifica JWT backend)
- [x] Registrazione, login, logout, reset password, conferma email (pagine + chiamate Supabase)
- [x] Middleware di protezione route autenticate (frontend e backend)
- [x] Gestione sessione scaduta (redirect a login)
- [x] Tabelle `users`, `organizations`, `organization_members` + migration Alembic
- [x] Invito collaboratori via email (token scadente) — endpoint pronto, invio email reale in Fase 7
- [x] Ruoli Admin/Viewer
- [x] Pagine "Profilo utente" e "Impostazioni organizzazione" (stub funzionanti)
- [x] Rate limiting login (10 tentativi / 15 min / IP)
- [x] Blocco account dopo tentativi falliti ripetuti
- [x] Audit log di ogni login (IP, timestamp, esito)
- [x] Sanitizzazione input, protezione base SQL injection/XSS (ORM parametrico + Pydantic)
- [x] Header di sicurezza HTTP (HSTS, X-Content-Type-Options, X-Frame-Options, CSP)
- [ ] Progetto Supabase reale collegato — **richiede credenziali reali del titolare** (placeholder
      pronti in `.env.example`)

## Fase 2 — Database e modello dati completo — ✅ completata (parti eseguibili da qui)
- [x] Migration con tutte le tabelle richieste dalla roadmap
- [x] Tabella `assessment_results` (storico, non sovrascrive: ogni assessment è una nuova riga)
- [x] Tabella `compliance_measures` (vincolo unico per organizzazione + misura)
- [x] Tabella `documents` (versionati, pronti per il collegamento a Supabase Storage in Fase 5)
- [x] Tabella `incidents` + `incident_notifications` (24h/72h/30gg, cascade delete)
- [x] Tabella `suppliers` + `supplier_questionnaires` (con `access_token` per compilazione
      senza account, Fase 4)
- [x] Tabella `subscriptions` (una per organizzazione, piano Free esplicito)
- [x] Indici su `organization_id`/`created_at`/`updated_at` sulle tabelle a maggior lettura
- [x] Row Level Security: script `infra/supabase/rls_policies.sql` con 21 policy su 13
      tabelle (isolamento per organizzazione + regole admin/viewer) — verificato
      sintatticamente, da eseguire sul progetto Supabase reale (richiede `auth.uid()`,
      disponibile solo lì)
- [x] Seed data realistico: `apps/api/scripts/seed_dev_data.py` (3 organizzazioni con profili
      NIS2 diversi, utenti, assessment, le 15 misure di conformità, documenti, un incidente
      con notifiche, fornitori con questionari, abbonamento)
- [x] Script di backup: `apps/api/scripts/backup_db.sh` (pg_dump formato custom, retention
      configurabile, pensato per cron oltre ai backup automatici già inclusi da Supabase)

## Verifica eseguita (non solo scritta: testata davvero)
- Backend Fase 0-1: avviato un vero PostgreSQL locale (via `pgserver`, senza Docker),
  generata e applicata la migration Alembic iniziale, eseguiti i test automatici (pytest).
- Backend Fase 2: migration generata e applicata su Postgres reale (14 tabelle totali,
  verificate via query su `information_schema`), script di seed eseguito con successo (3
  organizzazioni + tutti i dati collegati creati correttamente), script RLS eseguito senza
  errori di sintassi con uno stub della funzione `auth.uid()`.
- **16/16 test automatici passati** (9 Fase 1 + 7 nuovi sui modelli Fase 2: vincoli di
  unicità, cascade delete, relazioni).
- Backend: lint (`ruff`) e formattazione (`black`) puliti su tutto il codice, zero errori.
- Frontend: build di produzione Next.js completata con successo (12 route generate),
  `next lint` pulito, `tsc --noEmit` senza errori su tutto il codice TypeScript.
- Repository Git locale creato con commit iniziale in questa cartella.

## Fasi successive (non ancora iniziate)
Fase 3 (API complete sulle nuove tabelle), Fase 4 (frontend completo dei 4 moduli), Fase 5
(AI), Fase 6 (pagamenti), Fase 7 (email), Fase 8 (sicurezza estesa), Fase 9 (infrastruttura),
Fase 10 (performance), Fase 11 (lancio) — da eseguire un modulo alla volta, come da preferenza
espressa.
