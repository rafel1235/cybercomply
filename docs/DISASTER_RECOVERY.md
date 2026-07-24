# Backup e disaster recovery (Fase 9)

## Bug reale scoperto e corretto in questa fase

Prima di questa fase, ogni PDF generato (`POST /documents/{id}/pdf`) veniva scritto solo
su disco locale (`app/core/config.py: local_storage_path`). Su un host con filesystem
effimero come Render — che azzera il disco locale ad ogni deploy o riavvio del servizio
— questo avrebbe significato perdere silenziosamente tutti i PDF generati al primo
deploy successivo, mentre il database avrebbe continuato a riportare un `pdf_url`
valido, con un errore 404 alla prima richiesta di download. Non era un problema teorico:
è esattamente il comportamento che questa piattaforma avrebbe avuto una volta distribuita
su Render secondo `render.yaml`.

**Corretto**: `app/services/pdf_storage.py` carica i PDF su Supabase Storage quando
configurato (stessa service role key della Fase 8), con ripiego automatico su disco
locale se Supabase Storage non risponde o non è configurato — non cambia nulla nel
comportamento di sviluppo attuale (mai stato configurato un progetto Supabase reale in
questa sessione), ma rende l'applicazione corretta non appena lo sarà. Vedi
`tests/test_pdf_storage.py` per la verifica del round-trip e del fallback.

## Backup del database

Supabase include backup automatici giornalieri su tutti i piani, inclusi quelli
gratuiti (con retention più breve sui piani free rispetto ai piani Pro/Team). Nessuna
configurazione applicativa è necessaria: è un servizio del progetto Supabase stesso, da
verificare nella dashboard (Database → Backups) una volta creato il progetto reale.

Da fare una volta creato il progetto Supabase reale, prima del lancio commerciale (come
richiesto esplicitamente dalla roadmap — "testare il restore almeno una volta"):
1. Creare un backup manuale o attendere il primo backup automatico.
2. Eseguire un restore su un progetto Supabase separato (mai sul progetto di
   produzione), verificando che i dati tornino consistenti.
3. Misurare quanto tempo richiede il restore (RTO — Recovery Time Objective): serve per
   sapere realisticamente quanto durerebbe un'interruzione in caso di incidente serio.
4. Verificare la retention del piano scelto (RPO — Recovery Point Objective, cioè
   quanti dati nella finestra più recente si potrebbero perdere nel caso peggiore).

## Backup dei file (PDF generati)

Con Supabase Storage configurato (vedi sopra), i PDF sono soggetti agli stessi backup
del progetto Supabase del database — nessuna procedura separata da mantenere. Finché
Supabase Storage non è configurato e i PDF restano solo su disco locale (stato attuale
di questa sessione di sviluppo), non c'è comunque nulla da "backuppare" separatamente
in modo affidabile: sono comunque sempre rigenerabili on-demand dal contenuto strutturato
del documento già salvato nel database (`documents.content`), che è la vera fonte di
verità — il PDF è solo una sua rappresentazione derivata. Anche in caso di perdita totale
dello storage PDF, nessun dato è perso in modo irreversibile: basta rigenerare il PDF con
lo stesso endpoint che lo ha creato la prima volta.

## Procedura di disaster recovery (scenari)

### Scenario 1 — Il backend non risponde (Render down o crash dell'applicazione)
1. Controllare lo stato del servizio nella dashboard Render e i log applicativi.
2. Se il processo è crashato, Render lo riavvia automaticamente; se il problema persiste,
   effettuare un rollback all'ultimo deploy funzionante (Render mantiene la cronologia
   dei deploy, rollback con un click).
3. Se configurato, Sentry avrà già registrato l'eccezione con stack trace completo (Fase
   9 — vedi `docs/MONITORAGGIO.md`): è il primo posto da controllare per la causa.

### Scenario 2 — Il database Supabase non è raggiungibile
1. Controllare la pagina di stato di Supabase (status.supabase.com) per un'interruzione
   nota.
2. Se il progetto stesso è danneggiato (non solo un'interruzione temporanea), effettuare
   il restore dall'ultimo backup disponibile su un nuovo progetto Supabase, seguendo la
   procedura descritta sopra.
3. Aggiornare `DATABASE_URL`/`SUPABASE_URL`/le chiavi nelle variabili d'ambiente Render
   e Vercel se il progetto di destinazione è cambiato, poi ridistribuire.

### Scenario 3 — Dati cancellati per errore (non un guasto tecnico)
1. L'audit log (Fase 3/8, `audit_logs`, mai cancellato) permette di ricostruire cosa è
   stato fatto, da chi e quando — primo passo per capire l'entità del problema.
2. Per un ripristino puntuale (es. un'organizzazione cancellata per errore da
   `DELETE /gdpr/account`, Fase 8): la cancellazione applicativa è intenzionalmente
   irreversibile via API (coerente con il diritto alla cancellazione GDPR Art. 17), quindi
   l'unico ripristino possibile è dal backup del database Supabase (point-in-time
   recovery, se disponibile nel piano) verso un progetto temporaneo, da cui recuperare
   manualmente le righe necessarie.

### Scenario 4 — Chiave di cifratura dei campi sensibili persa (Fase 8)
Scenario particolarmente serio, già documentato in `.env.example`:
`FIELD_ENCRYPTION_KEY` non è recuperabile se persa, e senza di essa i valori cifrati
(P.IVA, dati incidente) restano illeggibili per sempre, anche ripristinando il database
da un backup — il backup del database conterrebbe comunque solo il testo cifrato. Per
questo la chiave stessa va conservata con un secret manager separato dal database (es.
il vault delle variabili d'ambiente di Render, non solo un file locale), mai solo sul
laptop di chi l'ha generata.

## Cosa NON è stato fatto in questa sessione

Nessun progetto Supabase reale è mai stato creato in questa sessione di sviluppo, quindi
nessun backup è mai stato realmente testato o ripristinato. Questo documento descrive la
procedura da seguire non appena un progetto reale esisterà, non un test già eseguito.
