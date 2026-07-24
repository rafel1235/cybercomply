# Ambienti: development, staging, production (Fase 9)

Tre ambienti separati, come richiesto dalla roadmap tecnica ("Ogni ambiente ha le sue
variabili d'ambiente separate, mai copiare prod su staging" — "Database separato per
staging e production, mai testare su dati reali"). Questo documento descrive come
ciascuno è realizzato concretamente con lo stack scelto (Vercel + Render + Supabase) e
la checklist di configurazione **una tantum** da fare a mano nelle rispettive dashboard
(nessuna di queste azioni può essere eseguita da codice: richiedono account reali mai
creati in questa sessione di sviluppo).

## Panoramica

| | Development | Staging | Production |
|---|---|---|---|
| Frontend | `next dev` locale | Vercel — deploy automatico ad ogni push su `main`, dominio tipo `staging.cybercomplyit.it` o l'URL `*.vercel.app` assegnato | Vercel — stesso deploy di staging promosso in produzione dopo l'approvazione GitHub, dominio `cybercomplyit.it` |
| Backend | `uvicorn` locale contro Postgres locale/`pgserver` | Render, servizio `cybercomplyit-api-staging` (`render.yaml`) | Render, servizio `cybercomplyit-api-production` (`render.yaml`) |
| Database | Postgres locale (dev) — mai usato dai test, che usano sempre un Postgres incorporato isolato (`pgserver`, vedi `tests/conftest.py`) | **Progetto Supabase dedicato a staging** (da creare) | **Progetto Supabase dedicato a production** (da creare) — mai lo stesso di staging |
| Variabili d'ambiente | `.env` locale (mai committato) | Secret della dashboard Render/Vercel per l'ambiente "staging" | Secret della dashboard Render/Vercel per l'ambiente "production" |
| `ENVIRONMENT` (backend) | `development` | `staging` | `production` |

Il codice è già scritto per comportarsi diversamente in produzione: `Settings.is_production`
(`app/core/config.py`) disabilita la documentazione Swagger (`/docs`) e aggiunge l'header
HSTS solo quando `ENVIRONMENT=production` (vedi `app/main.py` e
`app/core/middleware.py`, testato in `tests/test_security_headers.py`).

## Perché due progetti Supabase separati (non uno solo con due schemi)

La roadmap è esplicita: "mai testare su dati reali". Un progetto Supabase distinto per
staging significa che un test manuale, un bug, o un dato di prova non toccano mai
l'organizzazione di un cliente vero. Il costo aggiuntivo di un secondo progetto Supabase
(anche solo sul piano gratuito per staging) è trascurabile rispetto al rischio.

## Checklist di configurazione una tantum

### 1. Supabase (2 progetti)
- [ ] Creare un progetto Supabase per **staging** (region `eu-central-1`, Francoforte — GDPR)
- [ ] Creare un progetto Supabase per **production** (stessa region)
- [ ] Per ciascuno: applicare le migration Alembic (`alembic upgrade head` punta a
      `DATABASE_URL` di quel progetto), eseguire lo script RLS (Fase 2), copiare
      URL/anon key/service role key/JWT secret nelle rispettive variabili d'ambiente
      Render/Vercel (mai nel repository, mai in `.env` committato)

### 2. Render (`render.yaml` già pronto in questo repository)
- [ ] Collegare il repository GitHub a Render (Render legge `render.yaml` alla radice e
      propone di creare i due servizi `cybercomplyit-api-staging` e
      `cybercomplyit-api-production` automaticamente)
- [ ] Per ciascun servizio, compilare nella dashboard Render tutte le variabili con
      `sync: false` in `render.yaml` (`DATABASE_URL`, le chiavi Supabase, Stripe, Resend,
      Anthropic, `FIELD_ENCRYPTION_KEY`) con i valori del progetto Supabase corrispondente
      e le chiavi reali dei fornitori esterni quando disponibili
- [ ] In **Settings → Deploy** di ciascun servizio, generare un **Deploy Hook** e copiarne
      l'URL

### 3. GitHub (repository `rafel1235/cybercomply`)
- [ ] **Branch protection** su `main` (Settings → Branches → Add rule): richiedere almeno
      una review approvata e il passaggio dei check `backend`/`frontend` prima del merge —
      questo realizza "nessun push diretto su main, tutto passa da Pull Request"
      (`ci.yml` da solo non lo impone: è un'impostazione del repository, non del workflow)
- [ ] Creare l'ambiente GitHub **`staging`** (Settings → Environments → New environment):
      nessun reviewer obbligatorio, deploy automatico dopo che i test passano
- [ ] Creare l'ambiente GitHub **`production`**: aggiungere almeno un **required
      reviewer** — è questo che rende il deploy in produzione "manuale con approvazione"
      (il job `deploy-production` in `ci.yml` si mette in pausa finché non viene approvato
      a mano nella tab "Actions" del repository)
- [ ] Aggiungere i secret del repository (Settings → Secrets and variables → Actions):
      `RENDER_DEPLOY_HOOK_STAGING`, `RENDER_DEPLOY_HOOK_PRODUCTION` con gli URL generati
      al punto 2. Finché non sono impostati, la pipeline logga e salta il deploy senza
      fallire (vedi `ci.yml`)

### 4. Vercel (frontend)
- [ ] Collegare il repository GitHub a Vercel (Import Project), root directory
      `apps/web` — Vercel rileva Next.js automaticamente, non serve un `vercel.json`
- [ ] Impostare le variabili d'ambiente `NEXT_PUBLIC_SUPABASE_URL`,
      `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL` separatamente per gli
      scope **Preview** (punta al backend/Supabase di staging) e **Production** (punta al
      backend/Supabase di production) — Vercel supporta questa distinzione nativamente
      nelle impostazioni del progetto, non serve un file per ambiente nel repository
- [ ] Deploy automatico di produzione ad ogni push su `main` e deploy di anteprima per
      ogni Pull Request sono **comportamento nativo di Vercel** una volta collegato il
      repository (nessuna azione GitHub Actions dedicata: è esattamente quanto indicato
      dalla roadmap — "Vercel lo fa automaticamente")

### 5. Dominio e DNS
- [ ] Aggiungere il dominio `cybercomplyit.it` al progetto Vercel (Settings → Domains)
- [ ] Decidere la forma canonica (consigliato: apex `cybercomplyit.it` come canonico,
      `www.cybercomplyit.it` in redirect verso l'apex — ma è una preferenza di brand,
      entrambe le direzioni sono equivalenti dal punto di vista tecnico) e configurare il
      redirect nella stessa schermata "Domains" di Vercel (supporto nativo, non richiede
      modifiche a `next.config.js`)
- [ ] Configurare i record DNS presso il registrar del dominio secondo le istruzioni che
      Vercel mostra dopo aver aggiunto il dominio (tipicamente un record A verso l'IP di
      Vercel per l'apex e un CNAME per `www`); il certificato SSL viene emesso e rinnovato
      automaticamente da Vercel una volta che i record propagano
- [ ] Un sottodominio equivalente va collegato al servizio Render di staging (es.
      `staging.cybercomplyit.it` → CNAME verso l'host assegnato da Render), coerente con
      i valori già impostati in `render.yaml` (`ALLOWED_ORIGINS`, `FRONTEND_BASE_URL`)

## Cosa NON è stato fatto in questa sessione (richiede account reali)

Nessuna di queste azioni è stata eseguita: non esiste alcun account Render, Vercel o
progetto Supabase di staging/production creato da questa sessione di sviluppo. Il lavoro
di questa fase produce la configurazione (`render.yaml`, `ci.yml`) e questa checklist,
non l'infrastruttura stessa — coerente con lo stesso principio già seguito per
`ANTHROPIC_API_KEY`, le chiavi Stripe e `RESEND_API_KEY` nelle fasi precedenti: mai
generare o assumere credenziali reali, sempre lasciare un percorso chiaro e verificato
per quando saranno disponibili.
