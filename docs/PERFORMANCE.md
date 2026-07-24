# Performance (Fase 10)

## Frontend

### Bug reale scoperto e corretto: link interni come `<a>` invece di `next/link`

Trovati 5 collegamenti interni verso `/settings/billing` scritti come `<a href="/settings/billing">`
invece di `<Link href="/settings/billing">` (in `dashboard/compliance/page.tsx` — 2
occorrenze — e `settings/team/page.tsx` — 3 occorrenze). Un `<a>` per una route interna
forza un ricaricamento completo della pagina (nuova richiesta al server, ricaricamento di
tutto il JS, perdita dello stato React Query già in cache) invece di una transizione
lato client istantanea — l'esatto opposto di "prefetch delle route più usate" richiesto
dalla roadmap: un `<a>` non viene mai prefetchato. Corretti tutti e 5 in `next/link`,
verificato che il resto dell'app (inclusa `Sidebar.tsx`, già corretta) usi sempre
`next/link` per la navigazione interna (`grep` mirato su `<a href="/`, zero risultati dopo
la correzione).

### Bundle

Nessuna libreria pesante nelle dipendenze di produzione (`package.json`): solo
`@supabase/ssr`, `@supabase/supabase-js`, `@tanstack/react-query`, `zustand`, `next`,
`react`. Nessun chart/rich-text/date-picker esterno — il grafico di andamento della
dashboard (`ScoreTrendChart`) è SVG scritto a mano (Fase 4), non una libreria. Bundle di
produzione (`next build`), invariato rispetto a Fase 9: 19 route, JS condiviso 87.2 kB,
pagina più pesante (`/dashboard/compliance`) 176 kB first-load-JS — ragionevole per
un'app autenticata con Supabase + React Query, senza nulla da rimuovere. Non è stato
eseguito `@next/bundle-analyzer` come tool dedicato (non installato: avrebbe richiesto una
nuova dipendenza per un'analisi che l'output già dettagliato di `next build`, sopra,
copre a sufficienza per una bundle di queste dimensioni).

Non ci sono componenti client abbastanza pesanti da giustificare `next/dynamic` (lazy
loading): il code-splitting per-route dell'App Router di Next.js è già automatico e
sufficiente (ogni pagina è già il proprio chunk, come visibile nella tabella sopra).
`middleware.ts` (Edge, 81.8 kB) è quasi interamente `@supabase/ssr` per il controllo
sessione sulle route protette (`/dashboard`, `/settings`, tramite `matcher` — non gira su
route pubbliche): dimensione intrinseca alla libreria, non riducibile senza rimuovere il
controllo sessione stesso.

### Immagini e font: non applicabile

Nessuna immagine nell'app (cartella `public/` vuota, nessun tag `<img>` in tutto il
codice): `next/image` non ha nulla da ottimizzare. Nessun font esterno caricato (nessun
`next/font`, nessun `@font-face`): `globals.css` usa lo stack di font di sistema di
default di Tailwind — zero richieste di rete per i font, quindi zero rischio di FOUT per
costruzione, non perché ottimizzato a posteriori.

### Lighthouse: non eseguibile in questo ambiente

Il target "Lighthouse 90+" richiesto dalla roadmap non è stato misurato con lo strumento
reale: questo ambiente sandbox non ha Chrome/Chromium installato, e Lighthouse lo richiede
per funzionare (non disponibile via `npx` senza un download aggiuntivo di
Chrome+Lighthouse, non tentato per coerenza con i limiti di tempo per singolo comando già
riscontrati in questa sessione con altri strumenti pesanti). Le voci principali che
Lighthouse misurerebbe sono comunque coperte indirettamente da quanto sopra: bundle
ridotto e diviso per route, nessuna risorsa font/immagine da ottimizzare, navigazione
lato client corretta ovunque (prefetch). Da eseguire con Chrome reale (DevTools o
`npx lighthouse <url>`) contro un ambiente di staging reale, quando disponibile (Fase 9).

## Paginazione

La roadmap chiede esplicitamente "paginare tutte le liste (mai restituire array
illimitati)". Le liste che possono crescere nel tempo con l'uso della piattaforma
(documenti generati, incidenti, assessment eseguiti, fornitori, storico del punteggio di
conformità) ora accettano parametri `limit`/`offset` (default `limit=50`, massimo 200,
valori fuori range riportati in un intervallo sicuro invece di un errore 422) e
restituiscono il conteggio totale nell'header `X-Total-Count`.

Scelta deliberata: il corpo della risposta resta una lista semplice (`list[...]`), non un
involucro `{items, total}` — lo stesso pattern già in uso per `GET /audit-log` fin dalla
Fase 4. Questo significa che il frontend esistente continua a funzionare senza modifiche
(vede di default gli ultimi 50 elementi, più che sufficienti per qualunque organizzazione
di test reale), mentre l'header `X-Total-Count` resta disponibile per un'eventuale UI di
paginazione futura senza dover cambiare ancora il contratto della risposta. `GET
/organization/members` e `GET /compliance/measures` non sono stati toccati: il primo è
limitato per costruzione da `max_users` del piano, il secondo alle ~15 misure del
catalogo — nessuno dei due può crescere in modo illimitato.

Codice condiviso: `app/core/pagination.py` (`clamp_limit`, `clamp_offset`,
`apply_pagination`), usato da `documents.py`, `incidents.py`, `suppliers.py`,
`assessments.py`, `compliance.py` (`/history`).

## Bug reale scoperto e corretto: query N+1

Analizzando le liste per la paginazione, `list_incidents` e `list_suppliers`
serializzavano ogni riga leggendo una relazione (`incident.notifications` /
`supplier.questionnaires`) senza eager loading: con SQLAlchemy questo esegue una query SQL
separata per ogni riga della pagina, non un semplice dettaglio di stile. Verificato
concretamente in `tests/test_query_efficiency.py`, che conta le query SQL eseguite (via
l'evento `before_cursor_execute` di SQLAlchemy) confrontando una richiesta con 2 righe e
una con 8: prima della correzione, 8 query con 2 righe e 14 con 8 (esattamente +1 per ogni
riga aggiuntiva — la firma classica di un N+1); dopo la correzione (`selectinload` su
entrambe le relazioni), il conteggio resta identico indipendentemente dal numero di righe.
Il test è stato verificato in entrambe le direzioni: fallisce se si toglie
`selectinload` (riprodotto deliberatamente durante lo sviluppo), passa con la correzione.

## Indici mancanti, trovati con `EXPLAIN ANALYZE`

`documents`, `incidents`, `assessment_results` e `compliance_measures` avevano già un
indice composito `(organization_id, <colonna di ordinamento>)` corretto fin dalla Fase 2.
Analizzando le query più frequenti con `EXPLAIN ANALYZE` su un Postgres embedded popolato
con 20.000 righe di test, sono emersi due problemi reali:

- **`audit_logs` non aveva alcun indice oltre alla chiave primaria**, pur essendo la
  tabella con la crescita più rapida di tutto lo schema (una riga per ogni azione
  registrata) e interrogata ad ogni caricamento della dashboard. Prima della correzione,
  `GET /audit-log` degenerava in una scansione sequenziale + ordinamento (`Seq Scan` +
  `Sort`, 2.9 ms su 20.000 righe di una singola organizzazione — il costo cresce con il
  numero totale di righe nel database multi-tenant, non solo quelle dell'organizzazione).
  Dopo aver aggiunto `ix_audit_logs_org_created` e `ix_audit_logs_org_action_created`
  (migration `c4e8f1a9b7d3`), entrambe le query (`GET /audit-log` e `GET
  /compliance/history`) usano un `Index Scan Backward` diretto: 0.08 ms e 0.055 ms
  rispettivamente sullo stesso dataset — circa 35 volte più veloce, e il divario cresce
  ulteriormente con più organizzazioni nel database.
- **`suppliers` aveva già un indice `(organization_id, status)`** (pensato per un filtro
  per stato mai implementato) ma nessuno che copra l'ordinamento reale della lista
  (`created_at desc`). Aggiunto `ix_suppliers_org_created`.

## Tempi di risposta (`< 500ms`, esclusa generazione AI)

Misurati con `TestClient` (10 richieste per endpoint dopo un warm-up, su un'organizzazione
con 20 documenti generati) su Postgres embedded in questo ambiente sandbox — non un vero
ambiente di produzione, ma rappresentativo del costo applicativo/query puro, al netto
della latenza di rete reale:

| Endpoint | mediana | massimo |
|---|---|---|
| `GET /documents` | 21.7 ms | 31.1 ms |
| `GET /compliance/measures` | 22.1 ms | 24.7 ms |
| `GET /compliance/score` | 16.9 ms | 20.2 ms |
| `GET /compliance/history` | 20.6 ms | 27.4 ms |
| `GET /audit-log` | 19.4 ms | 20.1 ms |
| `GET /organization/members` | 21.2 ms | 23.5 ms |
| `GET /assessments` | 22.0 ms | 23.9 ms |

Tutti ben sotto il budget di 500ms richiesto dalla roadmap (esclusa la generazione
documenti con AI, che dipende dalla latenza dell'API Anthropic e non da questa
piattaforma). Da verificare di nuovo con dati di volume realistico su un ambiente di
produzione reale una volta disponibile (Fase 9).

## Caching: valutato, non implementato

La roadmap suggerisce di "aggiungere caching sulle query più frequenti (Redis o cache
in-memory)". Valutato esplicitamente e non implementato in questa fase: con gli indici
sopra, le query più frequenti rispondono già in sotto-millisecondo (vedi `EXPLAIN
ANALYZE`), e introdurre Redis (un servizio in più da gestire, monitorare e tenere
sincronizzato) non è giustificato senza un carico reale che lo richieda. Le uniche
strutture "cachate" oggi sono in-memory Python a costo zero e senza rischio di
disallineamento: il catalogo delle 15 misure di conformità
(`compliance_catalog.py`) e i limiti dei piani (`entitlements.PLAN_ENTITLEMENTS`), nessuno
dei due richiede una query. Da rivalutare se/quando le metriche di produzione reali (Fase
9 — Sentry, uptime monitoring) mostrassero un reale collo di bottiglia.

## Paginazione delle liste: cosa NON è stato costruito

Solo il limite lato backend (mai un array illimitato) e l'header `X-Total-Count`. Non è
stata costruita una UI di paginazione (pulsanti "pagina successiva", numero di pagina)
nel frontend: con i volumi di dati attuali (organizzazioni di test, uso reale non ancora
iniziato) i 50 elementi di default coprono sempre l'intera lista. Da costruire quando
il volume reale di un'organizzazione lo giustificherà.
