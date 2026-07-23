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

## Fase 3 — API completa — ✅ completata (parti eseguibili da qui)
- [x] Middleware globali: gestione errori centralizzata (404/422/500 con risposta JSON
      coerente), rate limiting per utente autenticato (oltre a quello per IP di Fase 1)
- [x] Endpoint organizzazione: `GET/PUT /organization`, `GET /organization/members`,
      `DELETE /organization/members/:id` (protezione ultimo admin), `POST
      /organization/invites`
- [x] Endpoint assessment: `POST /assessments` (classificazione NIS2/CRA automatica,
      storico mai sovrascritto), `GET /assessments/latest`, `GET /assessments`
- [x] Endpoint compliance: `GET /compliance/measures` (auto-provisioning delle 15 misure
      del catalogo ACN), `PATCH /compliance/measures/:id` (solo admin), `GET
      /compliance/score` (punteggio pesato conforme=1/parziale=0.5/non conforme=0), `GET
      /compliance/history` (storico ricostruito dagli eventi di audit
      `compliance.score_snapshot`, senza inventare dati né serve una tabella dedicata)
- [x] Endpoint documenti: `GET/POST /documents`, `GET/PUT/DELETE /documents/:id`, `POST
      /documents/generate` (contenuto segnaposto strutturato per tipo, versionato senza
      sovrascrivere lo storico), `POST /documents/:id/pdf` (PDF reale generato al volo,
      senza dipendenze esterne, salvato su storage locale in attesa di Supabase Storage)
- [x] Endpoint incidenti: `GET/POST /incidents`, `GET/PATCH /incidents/:id`, `POST
      /incidents/:id/close`, `POST /incidents/:id/notifications` (una sola notifica per
      fase per incidente, 409 se duplicata). Scadenze 24h/72h/30gg (NIS2) e 24h/72h (CRA
      verso ENISA) calcolate matematicamente da `opened_at`, con flag "scaduta" se non
      ancora inviata oltre il termine. `reference_code` progressivo per organizzazione e
      anno (es. INC-2026-003).
- [x] Endpoint fornitori: `GET/POST /suppliers`, `GET/PUT /suppliers/:id`, `DELETE
      /suppliers/:id` (solo admin), `POST/GET /suppliers/:id/questionnaires`. Endpoint
      pubblico separato (nessuna autenticazione, il possesso del token è la credenziale):
      `GET/POST /public/questionnaires/:token` — il fornitore compila senza account, lo
      stato di conformità viene calcolato dalle risposte (5 domande fisse: se tutte
      positive → conforme, nessuna → non conforme, altrimenti parziale) e sincronizzato
      sia sul questionario sia sulla scheda fornitore.

## Verifica eseguita (non solo scritta: testata davvero)
- Backend Fase 0-1: avviato un vero PostgreSQL locale (via `pgserver`, senza Docker),
  generata e applicata la migration Alembic iniziale, eseguiti i test automatici (pytest).
- Backend Fase 2: migration generata e applicata su Postgres reale (14 tabelle totali,
  verificate via query su `information_schema`), script di seed eseguito con successo (3
  organizzazioni + tutti i dati collegati creati correttamente), script RLS eseguito senza
  errori di sintassi con uno stub della funzione `auth.uid()`.
- **16/16 test automatici passati** (9 Fase 1 + 7 nuovi sui modelli Fase 2: vincoli di
  unicità, cascade delete, relazioni).
- Backend Fase 3 (assessment/compliance): migration esistenti riapplicate da zero su
  Postgres reale, **32/32 test automatici passati** (21 precedenti + 6 organizzazione/membri
  + 5 assessment + 6 compliance), lint (`ruff`) pulito su tutto il codice nuovo e
  preesistente, formattazione `black` applicata ai file nuovi/modificati di questo modulo.
- Backend Fase 3 (documenti): **39/39 test automatici passati** (32 precedenti + 7 nuovi),
  incluso un test che genera davvero un PDF, lo legge da disco e verifica che inizi con
  l'header `%PDF-1.4` (non un semplice controllo sulla risposta JSON). Lint pulito.
- Backend Fase 3 (incidenti): **47/47 test automatici passati** (39 precedenti + 8 nuovi:
  reference code progressivo, scadenze calcolate correttamente, chiusura idempotente,
  notifiche non duplicabili per fase, filtro per stato). Lint pulito.
- Backend Fase 3 (fornitori): **55/55 test automatici passati** (47 precedenti + 8 nuovi:
  CRUD fornitori, permessi admin/viewer sulla cancellazione, generazione token
  questionario, compilazione pubblica end-to-end con calcolo corretto dello stato
  conforme/parziale/non conforme, token sconosciuto rifiutato con 404). Lint pulito.
- **Verifica finale Fase 3**: aggiunti 5 test mirati per portare la copertura degli
  endpoint fornitori dal 72% al 100% (update campo per campo, criticità/stato invalidi,
  fornitore non trovato, elenco questionari). **60/60 test automatici passati in
  totale**, eseguiti da zero su un PostgreSQL reale (migration Fase 0-1-2 riapplicate).
  Copertura di `app/` misurata con `pytest-cov`: **97% (1332 statement, 45 non
  coperti)**, ben oltre il target dell'80% — le righe non coperte sono quasi tutte rami
  di errore secondari (es. `db/session.py` non usato nei test, che usano `db_session`).
  Lint (`ruff`) pulito su tutto il codice, backend e frontend precedentemente verificati
  restano intatti (nessuna modifica ai loro file in questa fase). Diff completo tra la
  copia di verifica e la cartella consegnata (`piattaforma/apps/api`): nessuna differenza
  a parte il file `.env` locale dell'utente (mai toccato, correttamente ignorato da git).
- Backend: lint (`ruff`) e formattazione (`black`) puliti su tutto il codice, zero errori.
- Frontend: build di produzione Next.js completata con successo (12 route generate),
  `next lint` pulito, `tsc --noEmit` senza errori su tutto il codice TypeScript.
- Repository Git locale creato con commit iniziale in questa cartella.

## Fasi successive (non ancora iniziate)
Fase 4 (frontend completo dei 4 moduli: assessment, compliance, documenti, incidenti,
fornitori), Fase 5 (generazione documenti con AI), Fase 6 (pagamenti), Fase 7 (email
transazionale), Fase 8 (sicurezza estesa), Fase 9 (infrastruttura/deploy), Fase 10
(performance), Fase 11 (lancio) — da eseguire un modulo alla volta, come da preferenza
espressa.
