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

## Fase 4 — Frontend completo dei moduli — ✅ completata e verificata
- [x] Setup: React Query (`QueryClientProvider`), sistema di toast globale (senza librerie
      esterne), hook `useApi()` (token Supabase sempre fresco), `ApiError` tipizzato con
      status HTTP, componenti UI riutilizzabili (`Badge`, `Skeleton`, `EmptyState`)
- [x] Endpoint `GET /audit-log` (dedicato alla dashboard: ultime azioni, limite 1-100,
      isolato per organizzazione)
- [x] Dashboard principale: indice di conformità, stato NIS2/CRA, prossime scadenze
      normative reali (estratte dalla Guida al Servizio), grafico andamento (SVG scritto a
      mano, nessuna libreria di charting), ultime azioni registrate
- [x] Modulo Assessment: form di classificazione, risultato con badge e motivazione,
      storico completo
- [x] Modulo Compliance Tracker: le 15 misure raggruppate in 6 categorie, filtro per stato,
      note per misura, cronologia per singola misura dall'audit log
- [x] Modulo Documenti: generazione, versionamento, anteprima, download PDF reale (nuovo
      endpoint `GET /documents/:id/pdf`), report di conformità stampabile (`window.print()`)
- [x] Modulo Incident Reporting: apertura incidente, timer live dall'apertura, checklist
      scadenze di notifica (NIS2 24h/72h/30gg + CRA-ENISA 24h/72h) con stato
      inviata/scaduta/in attesa, mini-form di registrazione notifica per fase, generatore di
      bozza email per CSIRT Italia/ENISA (copia negli appunti), chiusura incidente, export
      stampabile
- [x] Modulo Supply Chain: CRUD fornitori con criticità/stato, invio questionario con link
      pubblico univoco (token, nessun account richiesto), pagina pubblica
      `/questionario/:token` per la compilazione (fuori dal middleware di autenticazione),
      calcolo dello stato di conformità sincronizzato su questionario e scheda fornitore

**Nota sulla verifica di questa fase**: durante lo sviluppo, un tentativo di installare una
libreria (poi rimossa, i grafici sono infatti SVG scritti a mano) aveva corrotto
`apps/web/node_modules` nella cartella reale sincronizzata (symlink interni con errori di
I/O). Il problema era confinato del tutto a `node_modules` (nessun codice o dato utente a
rischio). Il titolare ha eseguito da PowerShell il reinstall (`Remove-Item -Recurse -Force
node_modules` + `pnpm install`) e poi la build reale:
- `pnpm --filter @cybercomplyit/web build` → **compilata con successo**, tutte le 17 route
  generate correttamente (incluse tutte le pagine nuove di questa fase: dashboard,
  assessment, compliance + report, incidenti + dettaglio, fornitori,
  `/questionario/:token` pubblica), type-checking Next.js incluso nella build senza errori.
- `pnpm --filter @cybercomplyit/web lint` → **nessun warning o errore ESLint**.

Fase 4 quindi confermata completa e verificata, non solo scritta.

## Fase 5 — Generazione documenti con AI — ✅ completata e verificata
- [x] `app/services/ai_client.py`: wrapper interno per l'API Messages di Claude via
      `httpx` (nessuna nuova dipendenza — niente SDK `anthropic`, per non ripetere i
      problemi di installazione avuti con `node_modules` in Fase 4). Retry con backoff
      esponenziale su 429/500/503/529, timeout 30s, ritorna token usati e durata per ogni
      chiamata.
- [x] `app/services/document_prompts.py`: un prompt per ciascuno dei 9 tipi di documento,
      con riferimenti normativi puntuali (articoli NIS2/CRA, sezioni Determinazione ACN
      164179/2025) e personalizzazione con i dati reali dell'organizzazione (settore,
      dipendenti, categoria NIS2/CRA dall'ultimo assessment).
- [x] `app/services/ai_document_generator.py`: orchestratore che sceglie AI o segnaposto.
      Se `ANTHROPIC_API_KEY` non è configurata, o la chiamata fallisce, o la risposta non è
      nel formato JSON atteso, ricade sempre sul contenuto segnaposto esistente — la
      generazione documenti non fallisce mai con un errore 500 per un problema lato AI.
- [x] `POST /documents/generate` aggiornato per usare l'orchestratore; l'audit event
      `document.generated` ora registra anche modello, token input/output, durata e costo
      stimato (se configurato) di ogni chiamata AI, per il monitoraggio spesa richiesto
      dalla roadmap.
- [x] PDF: rinominato `pdf_stub.py` → `pdf_renderer.py` (il vecchio nome resta come shim
      di compatibilità, non eliminabile in questo ambiente per permessi del filesystem
      sincronizzato). Aggiunta intestazione (organizzazione + titolo), piè di pagina
      (numero pagina, versione, data di generazione), e disclaimer quando il contenuto è
      stato scritto dall'AI. Ancora nessuna libreria di rendering HTML→PDF (WeasyPrint/
      Puppeteer): scelta deliberata per non introdurre nuove dipendenze in questo ambiente,
      da rivalutare su un'infrastruttura di produzione più stabile.

**Nota importante**: `ANTHROPIC_API_KEY` non è ancora stata impostata con un valore reale
(resta il placeholder di `.env.example`). Tutto il codice di generazione AI è scritto,
testato con chiamate mockate, e verificato che il fallback funzioni correttamente — ma non
è stato eseguito nemmeno una volta contro la vera API Claude in questa sessione. Quando
avrai una chiave reale, impostala in `apps/api/.env` come `ANTHROPIC_API_KEY` e verifica
un paio di generazioni reali prima di considerare la Fase 5 pronta per i clienti (in
particolare la qualità dei prompt, che la roadmap chiede di validare anche con un esperto
legale prima del lancio commerciale).

## Fase 6 — Pagamenti e piani — ✅ completata e verificata
- [x] Modello dei 4 piani (`docs/NUOVI PIANI.pdf`, tabella autoritativa) centralizzato in
      `app/services/entitlements.py`: una sola fonte di verità (`PLAN_ENTITLEMENTS`) per
      utenti massimi, documenti AI/mese, limite e modificabilità delle misure di
      conformità, Incident Reporting, Supply Chain, report trimestrali, white-label, API.
- [x] Ogni nuova organizzazione parte automaticamente con un trial Essential di 14 giorni
      senza carta di credito richiesta (`auth/sync`); allo scadere il downgrade a Free è
      "lazy" (calcolato alla richiesta successiva, nessun cron — l'infrastruttura per job
      schedulati arriva in Fase 9), e non cancella mai i dati: restano in sola lettura.
- [x] Gating applicato ai moduli esistenti: Incident Reporting e Supply Chain bloccati a
      livello di intero router (dependency su `APIRouter`) per i piani che non li
      includono; quota documenti AI/mese calcolata contando le righe generate dall'inizio
      del mese solare (nessun contatore separato da mantenere); Compliance Tracker
      limitato alle prime 3 misure e in sola lettura su Free; limite posti (`max_users`)
      verificato su ogni invito, contando membri attuali + inviti pendenti non scaduti.
      Il link pubblico di un questionario fornitore già inviato resta sempre valido anche
      se il piano dell'organizzazione cambia in seguito.
- [x] Integrazione Stripe (`app/services/billing.py`): Customer Stripe creato alla prima
      necessità e riusato, Checkout Session (abbonamento Essential/Business — Enterprise
      resta su contratto personalizzato, non acquistabile in autonomia), Customer Portal
      per gestione autonoma dell'abbonamento, webhook con verifica firma HMAC locale e
      gestione dei 5 eventi rilevanti (`checkout.session.completed`,
      `invoice.payment_succeeded`, `invoice.payment_failed`,
      `customer.subscription.deleted`, `customer.subscription.updated` per upgrade/
      downgrade fatti dal cliente stesso dal portale). Come per l'AI in Fase 5: se Stripe
      non è configurato le funzioni restituiscono un errore chiaro (400), mai un 500.
- [x] Endpoint `GET /billing/subscription` (piano/stato/trial/rinnovo/entitlement/utilizzo
      corrente), `POST /billing/checkout`, `POST /billing/portal` (entrambi solo admin),
      `POST /billing/webhook` (pubblico, verificato via firma Stripe, non tramite JWT).
- [x] Frontend — pagina `settings/billing`: piano attuale, stato (badge in prova/attivo/
      pagamento non riuscito/annullato), countdown del trial, prossimo rinnovo, utilizzo
      corrente (documenti/mese e utenti rispetto ai limiti), confronto dei 4 piani con
      pulsante "Passa a…" (Essential/Business, via Stripe Checkout) e "Contattaci" per
      Enterprise, pulsante "Gestisci abbonamento" (Customer Portal Stripe) quando esiste
      già un abbonamento a pagamento. Gestisce anche il redirect di ritorno da Stripe
      (`?checkout=success|cancelled`).
- [x] Gating visivo nel resto della UI: voci di navigazione Incident Reporting/Supply
      Chain contrassegnate "UPGRADE" quando non incluse nel piano (il link resta
      cliccabile: la pagina di destinazione mostra l'upsell completo se il backend
      risponde 403); badge del piano e countdown del trial nell'header; Compliance
      Tracker mostra un avviso e disabilita modifica/note quando il piano è in sola
      lettura (Free); tab Documenti mostra il contatore "X / Y generati questo mese" e
      disabilita il pulsante di generazione al raggiungimento della quota; pagina Team
      riscritta per usare i veri endpoint `/organization/*` (prima puntava a un endpoint
      Fase 1 non più esistente, quindi ogni invito falliva silenziosamente: bug
      preesistente scoperto e corretto in questa fase) con messaggio esplicito e link
      alla pagina Fatturazione quando si raggiunge il limite di posti del piano.

**Nota importante**: come per `ANTHROPIC_API_KEY` in Fase 5, Stripe non è mai stato
chiamato con credenziali reali in questa sessione — tutte le chiamate SDK sono state
sostituite con doppi di test (`monkeypatch`), sia per non dipendere da credenziali reali
sia per non generare veri addebiti durante i test automatici. Prima del lancio commerciale
vanno impostate le chiavi reali (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
`STRIPE_PRICE_ID_ESSENTIAL`, `STRIPE_PRICE_ID_BUSINESS`) in `apps/api/.env` e va eseguito
almeno un ciclo completo di checkout/webhook contro l'ambiente di test di Stripe.

## Fase 7 — Email transazionali e notifiche — ✅ completata e verificata
- [x] **Bug scoperto e corretto prima di poter partire**: dopo la conferma email,
      `/auth/sync` non veniva mai chiamato (solo `login.tsx` lo chiamava, e solo dopo un
      login con password) — un utente che confermava l'email e andava dritto in
      dashboard non aveva mai un'organizzazione creata. `confirm/page.tsx` ora chiama
      `/auth/sync` con i metadati salvati alla registrazione (nome azienda, nome
      completo), che prima andavano persi perché `login.tsx` inviava un body vuoto.
- [x] **Flusso di accettazione invito**, mai esistito prima d'ora: `OrganizationInvite`
      veniva creato ma non c'era alcun modo di redimerlo — chi si registrava con
      l'email invitata otteneva comunque una propria organizzazione nuova. Aggiunto
      endpoint pubblico `GET /public/invites/{token}` (anteprima senza autenticazione,
      come per i questionari fornitori), `SyncUserRequest.invite_token`, e
      `sync_user` che unisce l'utente all'organizzazione dell'invito (con il ruolo
      scelto dall'admin) invece di crearne una nuova — solo se il token è valido, non
      scaduto, non già accettato, e per l'email corrispondente (altrimenti ignorato in
      silenzio, stesso principio di degradazione controllata di AI/Stripe). Pagina di
      registrazione aggiornata per leggere `?invite=token`, mostrare "Stai per unirti
      a…" e passare il token attraverso Supabase fino al momento della conferma email.
- [x] `app/services/email_service.py`: invio email transazionali via l'API REST di
      Resend (solo `httpx`, nessun SDK nuovo, stesso principio del client AI di Fase 5).
      Se `RESEND_API_KEY` non è configurata, o la chiamata a Resend fallisce, l'invio
      viene semplicemente saltato e loggato — mai un'eccezione: nessuna email può far
      fallire la registrazione, un invito, o un webhook di pagamento.
- [x] `app/services/email_templates.py`: wrapper HTML brandizzato responsive (stile
      inline, struttura a tabella per compatibilità Gmail/Outlook) più 11 template —
      benvenuto, invito team, pagamento riuscito (con link fattura da Stripe se
      disponibile)/fallito, abbonamento annullato, trial in scadenza (7gg/1gg) e scaduto,
      scadenza normativa NIS2/CRA in avvicinamento, incidente aperto senza notifica 24h,
      fornitore fermo da 6+ mesi, report mensile di conformità.
- [x] Email collegate agli eventi che accadono già in una request: benvenuto (nuova
      organizzazione in `sync_user`), invito (creazione invito in `organization.py`),
      pagamento riuscito/fallito/abbonamento cancellato (i 3 handler webhook di Stripe
      già scritti in Fase 6, ora inviano email a tutti gli admin dell'organizzazione).
- [x] `scripts/send_scheduled_emails.py`: le email che richiedono una scansione
      periodica (trial in scadenza/scaduto, scadenze NIS2/CRA, incidente senza notifica
      24h, fornitore fermo, report mensile) non hanno ancora un vero scheduler (arriva
      in Fase 9): script eseguibile manualmente ora, con funzioni testabili
      singolarmente e pronte per un cron reale. Idempotente tramite l'audit log come
      marcatore "già inviato" (un'action dedicata per alert, con l'identificativo
      incorporato dove serve un promemoria per-entità), così eseguirlo più volte lo
      stesso giorno non invia email duplicate. Riusa direttamente il calcolo dello score
      di `GET /compliance/score` per il report mensile, invece di duplicarlo.

**Nota importante**: come per `ANTHROPIC_API_KEY` (Fase 5) e le chiavi Stripe (Fase 6),
`RESEND_API_KEY` non è mai stata impostata con un valore reale in questa sessione — ogni
invio è stato verificato con `httpx.post` sostituito da un doppio di test. Prima del
lancio commerciale vanno: impostata una chiave Resend reale, verificato il dominio
mittente (SPF/DKIM/DMARC) altrimenti le email finiscono in spam o vengono rifiutate, e
collegato `scripts/send_scheduled_emails.py` a un vero cron giornaliero (Fase 9).

**Scelta deliberata, fuori dal perimetro di questo backend**: conferma registrazione e
reset password restano email native di Supabase Auth (già funzionanti, mai in questa
sessione sostituite), non email inviate da CyberComplyIT. Personalizzarle graficamente
richiede configurare l'SMTP custom sul progetto Supabase reale (dashboard, non codice):
da fare quando il progetto Supabase reale sarà collegato.

## Fase 8 — Sicurezza del prodotto — ✅ completata e verificata
- [x] **Header di sicurezza HTTP**: `SecurityHeadersMiddleware` (backend) esteso con
      `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`
      (CSP `default-src 'none'` già presente da Fase 1, corretta per un'API JSON pura).
      `next.config.js` (frontend) ora imposta `poweredByHeader: false`, una CSP costruita
      dinamicamente dagli URL Supabase/API effettivi, `Permissions-Policy` e HSTS. Aggiunto
      `robots.txt` che esclude le route autenticate (`/dashboard`, `/settings`). Verificato
      via audit del codice che non ci sono query SQL costruite per concatenazione di
      stringhe (solo ORM parametrizzato) né `dangerouslySetInnerHTML` nel frontend.
- [x] **Cifratura a riposo** dei dati sensibili esplicitamente citati dalla roadmap: P.IVA
      (`organizations.vat_number`) e dati incidente (`incidents.data`). Cifratura simmetrica
      Fernet (`cryptography`, già dipendenza transitiva) applicata in modo trasparente via
      un `TypeDecorator` SQLAlchemy (`app/db/encrypted_types.py`): nessuna route, schema o
      test esistente ha dovuto cambiare per continuare a leggere/scrivere questi campi in
      chiaro lato applicazione. Un prefisso `enc::` distingue i valori cifrati da quelli
      scritti prima di questa fase (retrocompatibile, nessun backfill necessario). Se
      `FIELD_ENCRYPTION_KEY` non è configurata, i valori vengono salvati in chiaro con un
      warning nei log — mai generata una chiave effimera, per non rischiare di rendere
      irrecuperabili per sempre dati già cifrati con una chiave persa.
- [x] **GDPR — Art. 20, esporta i miei dati**: `GET /gdpr/export` restituisce un export
      completo e strutturato di tutti i dati riconducibili all'utente autenticato — il
      proprio profilo e, per ciascuna organizzazione di cui è membro, membri, assessment,
      misure di compliance, documenti, incidenti (con le scadenze di notifica calcolate),
      fornitori e audit log. Riusa le stesse funzioni di serializzazione (`_to_out`) già
      usate dai rispettivi endpoint, invece di duplicarle, così l'export non può divergere
      dal formato mostrato nell'app. I valori cifrati (P.IVA, dati incidente) tornano in
      chiaro nell'export, come in ogni altra lettura autenticata. L'export stesso genera un
      evento di audit (`gdpr.data_exported`). Frontend: sezione "Privacy e dati" nella
      pagina Profilo con un pulsante che scarica l'export come file JSON (stesso pattern già
      usato per il download dei PDF dei documenti — nessuna navigazione, link temporaneo in
      memoria).
- [x] **GDPR — Art. 17, cancella il mio account**: `DELETE /gdpr/account` esegue subito
      (non in coda, ben entro i 30 giorni previsti dalla roadmap) la cancellazione
      dell'account. Per ogni organizzazione di cui l'utente è membro: se ne è l'unico
      membro, l'intera organizzazione viene cancellata a cascata (membri, assessment,
      misure, documenti, incidenti, fornitori, abbonamento); se è l'unico admin con altri
      membri, l'operazione viene rifiutata (400) chiedendo di promuovere prima un altro
      admin — stessa regola già applicata da `DELETE /organization/members/{user_id}`;
      altrimenti viene rimossa solo la sua iscrizione, organizzazione e altri membri
      restano intatti. Tutte le organizzazioni sono validate prima di cancellare
      qualunque cosa, per non lasciare mai una cancellazione a metà. L'eventuale
      cancellazione dell'utente su Supabase Auth (Admin API) è "best effort": non blocca
      mai la cancellazione dello specchio locale, l'unica parte realmente sotto il
      controllo diretto di questa API (mai stata configurata con credenziali reali in
      questa sessione, vedi nota più sotto). L'audit log delle organizzazioni cancellate
      non viene perso (`organization_id` va a `NULL` via `ondelete="SET NULL"`, i record
      restano per la conservazione minima di 12 mesi). Frontend: sezione "Zona
      pericolosa" nella pagina Profilo, dietro una conferma esplicita (l'utente deve
      digitare "ELIMINA"), che poi effettua il logout e reindirizza al login.
- [x] **Documenti GDPR**: `docs/REGISTRO_TRATTAMENTI.md`, un vero Registro delle Attività
      di Trattamento (Art. 30) ricostruito dal modello dati reale (non un template) —
      categorie di interessati e dati, finalità e basi giuridiche, i 4 fornitori esterni
      che trattano dati per conto di CyberComplyIT (Supabase, Stripe, Resend, Anthropic)
      con le note sui DPA e i trasferimenti extra-UE ancora da verificare legalmente,
      misure di sicurezza, tempi di conservazione, ed esplicita valutazione (non
      decisione) sulla necessità di un DPO. Pagina pubblica `/cookie-policy` (frontend):
      onesta, non generica — spiega perché non serve un banner di consenso (nessuna
      libreria di analytics/tracciamento nel codice, verificato), l'unico cookie è quello
      di sessione tecnico di Supabase Auth, e chiarisce che Stripe (pagine hostate,
      dominio esterno) ha una propria informativa. Linkata dal footer di tutte le pagine
      pubbliche di autenticazione (`AuthLayout`).

**Nota**: come da roadmap, alcuni requisiti di Fase 8 non sono task di codice e restano
esplicitamente fuori da questa sessione — vedi la nota nella sezione "Fasi successive" in
fondo a questo documento, e il §3 di `docs/REGISTRO_TRATTAMENTI.md` per l'elenco completo
lato GDPR (Privacy Policy/Cookie Policy vere e proprie con un avvocato, DPA con i
fornitori, verifica dei trasferimenti extra-UE, decisione sul DPO, GitHub Secret
Scanning).

## Fase 9 — Infrastruttura e deploy — ✅ completata e verificata
- [x] **CI/CD**: `.github/workflows/ci.yml` riscritto da zero (la versione preesistente
      eseguiva solo lint+test senza Postgres raggiungibile: sarebbe fallita al primo run
      reale). Pipeline in 4 job: `backend` (ruff, black --check, pytest con copertura),
      `frontend` (tsc, next lint, next build), `deploy-staging` (solo su push a `main`,
      dopo che backend e frontend sono passati, `environment: staging`) e
      `deploy-production` (dopo staging, `environment: production`) — l'approvazione
      manuale richiesta dalla roadmap prima della produzione si ottiene con i Required
      Reviewers dell'Environment `production` su GitHub (impostazione da fare nella
      dashboard del repository, non esprimibile in YAML).
- [x] **Correzione di sicurezza scoperta preparando la CI**: `tests/conftest.py` avviava
      Postgres embedded solo se non c'era già un `DATABASE_URL` — se per qualunque motivo
      un `DATABASE_URL` reale fosse stato presente nell'ambiente (es. un `.env` con
      credenziali vere), eseguire `pytest` avrebbe cancellato/ricreato le tabelle su un
      database reale. Corretto forzando Postgres embedded (`pgserver`) in ogni caso,
      prima ancora di importare l'applicazione: i test non possono più, per costruzione,
      toccare un database che non sia quello effimero creato per loro.
- [x] **Ambienti**: `docs/AMBIENTI.md` — strategia a 3 ambienti (dev/staging/production),
      due progetti Supabase separati (staging e produzione, mai lo stesso database),
      checklist operativa completa e numerata (Supabase, Render, GitHub, Vercel, dominio
      e DNS) per quando il titolare avrà gli account reali: nessuno di questi passaggi è
      eseguibile da qui, richiedono tutti una dashboard reale.
- [x] **Config hosting**: `render.yaml` (Infrastructure as Code) con due servizi web
      (`cybercomplyit-api-staging`, `cybercomplyit-api-production`), regione Francoforte
      (UE, per il vincolo GDPR), `autoDeploy: false` su entrambi — il deploy parte solo
      dalla pipeline CI dopo che i test sono passati, mai automaticamente ad ogni push.
      `apps/web/vercel.json` con `regions: ["fra1"]` per lo stesso motivo (Vercel ha già
      integrazione nativa GitHub per il deploy automatico e le preview delle PR, non
      serve un job CI dedicato).
- [x] **Bug reale scoperto e corretto in questa fase**: i PDF generati venivano scritti
      solo su disco locale. Su un host con filesystem effimero come Render (azzerato ad
      ogni deploy) questo significa perdere silenziosamente tutti i PDF al primo deploy
      successivo, con il database che continua a riportare un `pdf_url` valido e un 404
      alla prima richiesta di download. Corretto con `app/services/pdf_storage.py`: carica
      su Supabase Storage quando configurato (stesse credenziali della Admin API di Fase
      8), con ripiego automatico e trasparente su disco locale se Supabase Storage non
      risponde o non è configurato — nessun comportamento esistente cambia finché non si
      passa a un ambiente reale con Storage configurato (mai successo in questa sessione).
- [x] **Monitoraggio**: Sentry error tracking, sia backend (`app/core/monitoring.py`,
      inizializzato solo se `SENTRY_DSN` è reale, cattura anche le eccezioni gestite dal
      middleware globale) sia frontend (`@sentry/nextjs`, convenzione App Router —
      `instrumentation.ts` + `instrumentation-client.ts` + config server/edge). Il wrapping
      Sentry di `next.config.js` è condizionato alla presenza di `NEXT_PUBLIC_SENTRY_DSN`
      per non appesantire ogni build quando non è configurato (stato attuale). Uptime
      monitoring (Better Uptime/UptimeRobot puntato su `/health`) e il dashboard nativo dei
      costi Anthropic restano configurazioni esterne, documentate in
      `docs/MONITORAGGIO.md` ma non eseguibili da qui.
- [x] **Backup e disaster recovery**: `docs/DISASTER_RECOVERY.md` — backup automatici
      giornalieri di Supabase (inclusi su ogni piano), procedura di restore-test da
      eseguire almeno una volta prima del lancio (mai eseguita in questa sessione, nessun
      progetto Supabase reale esiste ancora), e un runbook per 4 scenari concreti (backend
      irraggiungibile, database irraggiungibile, cancellazione per errore, perdita della
      chiave di cifratura Fase 8 — quest'ultima irreversibile per costruzione, da
      conservare in un secret manager separato dal database).

**Nota importante**: nessun account reale (Render, Vercel, Sentry, dominio) è mai stato
creato o collegato in questa sessione — ogni integrazione degrada in modo controllato
quando non configurata, esattamente come Anthropic/Stripe/Resend nelle fasi precedenti.
La pipeline CI/CD non è mai stata eseguita su un runner GitHub reale (nessun repository
remoto collegato in questa sessione): verificata leggendo ed eseguendo localmente ogni
comando che contiene, non osservandola girare su GitHub.

## Verifica eseguita (non solo scritta: testata davvero)
- **Verifica finale Fase 9**: nessuna nuova migration in questa fase. **213/213 test
  automatici passati** (205 precedenti + 8 nuovi per `pdf_storage.py`: salvataggio/lettura
  locale invariati quando Supabase Storage non è configurato, upload e download da
  Supabase Storage con `httpx` sostituito da un doppio di test, ripiego automatico su
  disco locale se l'upload fallisce, nessuna perdita del PDF in nessuno scenario).
  Copertura (`pytest-cov`): **96% (2298 statement, 87 non coperti)** — la riga scoperta più
  significativa resta `app/services/supabase_admin.py` (43%, stesso motivo delle fasi
  precedenti: mai configurato con credenziali reali). Lint (`ruff`) e formattazione
  (`black --check`) puliti su `app/`, `tests/` e `migrations/`. Frontend: `tsc --noEmit`
  pulito, `next lint` pulito, `next build` completata con successo con le stesse **19
  route** di Fase 8 (nessuna nuova pagina in questa fase, solo infrastruttura) —
  verificato sia il percorso di default (senza `NEXT_PUBLIC_SENTRY_DSN`, build rapida,
  invariata) sia che il wrapping condizionale di Sentry in `next.config.js` produca una
  configurazione valida quando il DSN è impostato (una build completa con un DSN finto
  supera il limite di tempo di questo ambiente sandbox per il lavoro aggiuntivo del
  plugin webpack di Sentry — limite noto della sandbox di sviluppo, non un difetto del
  codice: verificato che il modulo si carica e produce una config valida senza eccezioni).
  Diff completo tra la copia di verifica Linux e la cartella consegnata: nessuna
  differenza su tutti i file toccati in questa fase.
- **Verifica finale Fase 8**: migration esistenti riapplicate da zero su Postgres reale
  più la nuova migration di cifratura (`vat_number`/`incidents.data` da tipo nativo a
  `TEXT` opaco), **199/199 test automatici passati** (181 precedenti + 3 header di
  sicurezza + 10 cifratura campi + 2 export GDPR + 6 cancellazione account GDPR —
  quest'ultimi verificano end-to-end i tre esiti possibili: organizzazione cancellata per
  intero, iscrizione rimossa con organizzazione intatta, operazione rifiutata se unico
  admin con altri membri, oltre agli eventi di audit generati e all'inutilizzabilità del
  token dopo la cancellazione). Copertura (`pytest-cov`): **96% (2219 statement, 82 non
  coperti)** — le righe scoperte sono quasi tutte rami di errore secondari o percorsi che
  richiedono credenziali reali mai configurate in questa sessione (`app/services/
  supabase_admin.py` al 61% è il caso più basso, per lo stesso motivo di `ai_client.py`
  in Fase 5: la vera chiamata HTTP a un servizio esterno non configurato non è mai
  esercitata). Un bug scoperto e corretto durante lo sviluppo dei test di cancellazione
  account: la proprietà `supabase_admin_configured` considerava configurato l'URL/la
  chiave segnaposto di `.env.example`, causando un tentativo di vera chiamata HTTP
  (fallita per la configurazione di rete della sandbox) invece di saltare l'operazione
  come da progettazione — corretto con lo stesso guard "not startswith
  replace-with/YOUR-PROJECT" già usato per Stripe/Resend/cifratura, e reso
  `delete_auth_user` robusto anche a eccezioni impreviste (non solo `httpx.HTTPError`),
  coerentemente con la garanzia "mai un'eccezione" del resto del modulo. Lint (`ruff`)
  pulito su tutto `app/` e `tests/`, formattazione (`black --check`) pulita su tutti i
  file nuovi/modificati di questa fase (alcuni file di modelli invariati da fasi
  precedenti risultano non formattati secondo la versione attuale di `black`: non
  toccati, stessa scelta già fatta in Fase 7 per non introdurre modifiche estranee al
  perimetro della fase).
- Frontend Fase 8: `tsc --noEmit` pulito, `next lint` pulito, `next build` completata con
  successo — **19 route** (le 18 precedenti, invariate, più la nuova `/cookie-policy`
  pubblica e statica; l'export e la cancellazione account GDPR sono sezioni aggiunte alla
  pagina `/settings/profile` esistente, non nuove route).
- Diff completo tra la copia di verifica Linux e la cartella consegnata
  (`piattaforma/apps/api` e `piattaforma/apps/web`): nessuna differenza, file per file,
  su tutti i file toccati in questa fase.
- Backend Fase 7: migration esistenti riapplicate da zero su Postgres reale (nessuna
  nuova tabella in questa fase), **178/178 test automatici passati** (165 precedenti +
  13 nuovi: redenzione invito valido/email sbagliata/scaduto/già accettato, anteprima
  pubblica invito nei 4 casi, invio email mockato per benvenuto/invito/pagamento
  riuscito/fallito/abbonamento cancellato con verifica esplicita del destinatario e del
  contenuto, e l'intero script di alert schedulati — trial in scadenza a 7/1 giorni e
  idempotenza, trial scaduto con downgrade effettivo, scadenze NIS2 nei 2 casi "stessa
  data = 2 email distinte" e "fuori finestra = nessuna email", incidente scoperto dopo
  20h/già notificato/chiuso, fornitore mai valutato/valutato di recente, report mensile
  e relativa idempotenza, aggregatore `run_all`). Copertura: **96%** (2006 statement, 74
  non coperti). Lint (`ruff`) e formattazione (`black`) puliti su tutti i file
  nuovi/modificati di questa fase (alcuni file di modelli invariati da fasi precedenti
  risultano non formattati secondo la versione attuale di `black`: non toccati, per non
  introdurre modifiche estranee al perimetro di questa fase).
- Frontend Fase 7: `tsc --noEmit` pulito, `next lint` pulito, nessun warning, sulle
  pagine modificate (`register`, `confirm`).
- Backend Fase 6: migration riapplicata da zero su Postgres reale (colonna
  `stripe_customer_id` + indice), **132/132 test automatici passati** (86 precedenti + 46
  nuovi: entitlements per piano, trial e relativo downgrade automatico, integrazione
  Stripe interamente mockata — customer, checkout, portale, webhook con firma valida/non
  valida/segreto assente, i 5 eventi gestiti più i casi "customer sconosciuto" ed "evento
  non gestito" — ed enforcement dei limiti nei moduli Documenti/Compliance/Incident
  Reporting/Supply Chain/Organizzazione). Tre file di test preesistenti (fornitori,
  inviti organizzazione, audit log) sono stati aggiornati per portare esplicitamente
  l'organizzazione di test al piano Business dove necessario, dato che ora ogni nuova
  organizzazione parte in trial Essential (non più senza restrizioni come prima di questa
  fase) — con test dedicati aggiunti per verificare anche il comportamento bloccato.
  Copertura: **96%** (1842 statement, 73 non coperti). Lint (`ruff`) e formattazione
  (`black`) puliti su tutti i file nuovi/modificati di questa fase.
- Frontend Fase 6: verificato con un'installazione pulita di `pnpm` in un ambiente Linux
  dedicato (per evitare il problema di `node_modules` sincronizzato incontrato in Fase 4),
  cosa che ha permesso — a differenza della Fase 4 — di eseguire anche `next build` in
  proprio invece di doverlo delegare al titolare. **`tsc --noEmit` pulito** (corretto anche
  un errore di tipo preesistente e non collegato a questa fase: al campo `disclaimer` di
  `DocumentContent`, già usato dalla UI dei documenti dalla Fase 5, mancava la
  dichiarazione TypeScript). **`next lint` pulito, nessun warning**. **`next build`
  completata con successo**, tutte le 18 route generate (17 precedenti + la nuova
  `/settings/billing`), type-checking incluso nella build senza errori. Corretto inoltre un
  bug preesistente scoperto durante questo lavoro: `settings/team` chiamava un endpoint di
  invito della Fase 1 (`/auth/organizations/:id/invites`) mai più esistito dopo il
  refactor della Fase 3, quindi ogni invito falliva; ora usa il vero endpoint
  `/organization/invites` con elenco membri, rimozione e messaggio di limite posti.
- Backend Fase 5: migration riapplicate da zero su Postgres reale, **86/86 test
  automatici passati** (65 precedenti + 21 nuovi: retry/backoff/timeout del client AI con
  chiamate HTTP mockate, fallback al segnaposto in tutti i casi previsti — non configurata,
  JSON non valido, numero di sezioni sbagliato, eccezione dopo i retry — parsing corretto
  di una risposta AI valida anche se avvolta in un blocco ```json, e verifica che l'audit
  log registri token/costo/modello). **Nessuna chiamata reale all'API Claude eseguita**:
  `ANTHROPIC_API_KEY` non è ancora impostata con un valore vero. Copertura: **96%** (1531
  statement, 62 non coperti — quasi tutti rami di errore secondari; il file
  `pdf_stub.py`, ora solo uno shim di compatibilità non più importato da nessuno, è
  l'unico a 0% e non è un problema). Lint (`ruff`) e formattazione (`black`) puliti su
  tutti i file nuovi/modificati di questa fase.
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
Fase 10 (performance), Fase 11 (lancio) — da eseguire un modulo alla volta, come da
preferenza espressa. Nota: `scripts/send_scheduled_emails.py` ha ora una pipeline CI/CD
pronta (Fase 9) ma non è ancora collegato a un vero cron giornaliero — questo richiede un
account Render/GitHub reale (Render Cron Job o GitHub Actions schedulato) e resta da fare
appena quegli account esisteranno; anche il downgrade trial→Free resta calcolato "lazy"
alla richiesta, non ancora spostato su un cron.

Prima del lancio commerciale vanno anche: impostata una vera `ANTHROPIC_API_KEY` e
validati i prompt con un esperto legale (Fase 5); impostate le chiavi Stripe reali ed
eseguito un ciclo di checkout/webhook contro il suo ambiente di test (Fase 6); impostata
una vera `RESEND_API_KEY` con dominio mittente verificato SPF/DKIM/DMARC (Fase 7); tutti i
compiti non tecnici elencati nella nota di chiusura della Fase 8 e nel §3 di
`docs/REGISTRO_TRATTAMENTI.md` (Privacy Policy/Cookie Policy con un avvocato, DPA con
Supabase/Stripe/Resend/Anthropic, verifica dei trasferimenti extra-UE, decisione sul DPO,
GitHub Secret Scanning una volta pubblicato il repository); e, da Fase 9, la creazione
effettiva degli account Render/Vercel/Sentry/Supabase (staging+produzione) e dominio
seguendo `docs/AMBIENTI.md`, con almeno un ciclo di restore-test del backup seguendo
`docs/DISASTER_RECOVERY.md`.
