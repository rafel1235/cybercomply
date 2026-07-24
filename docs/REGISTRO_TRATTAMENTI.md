# Registro delle Attività di Trattamento (Art. 30 GDPR)

**Titolare del trattamento**: CyberComplyIT
**Ultimo aggiornamento**: 24 luglio 2026 (Fase 8 — Sicurezza del prodotto)

> Questo registro è stato ricostruito direttamente dal modello dati e dall'architettura
> reali della piattaforma (`apps/api/app/models/`, integrazioni esterne effettivamente
> configurate nel codice), non da un template generico. Va rivisto e firmato da chi riveste
> formalmente il ruolo di Titolare prima di essere considerato operativo a tutti gli
> effetti, ed eventualmente integrato da un legale con le informazioni societarie mancanti
> (dati del Titolare, eventuale DPO, sede legale).

## 1. Attività di trattamento: erogazione della piattaforma SaaS di compliance NIS2/CRA

### 1.1 Categorie di interessati

| Interessato | Descrizione |
|---|---|
| Utenti registrati | Persone fisiche che creano un account per conto della propria organizzazione (titolari d'azienda, responsabili IT/sicurezza, collaboratori invitati) |
| Fornitori terzi dei clienti | Persone che compilano il questionario di sicurezza fornitori tramite link pubblico, senza creare un account (`SupplierQuestionnaire`) |

### 1.2 Categorie di dati personali trattati

| Categoria | Campi/tabelle | Note |
|---|---|---|
| Dati identificativi e di contatto | `users.email`, `users.full_name` | Specchio locale dell'account Supabase Auth, che resta l'unica fonte di verità per le credenziali (nessuna password gestita da CyberComplyIT) |
| Dati aziendali del cliente | `organizations.vat_number` (cifrato a riposo), `sector`, `employee_count`, `annual_revenue_eur` | La P.IVA identifica l'azienda, non necessariamente una persona fisica, ma è trattata con la stessa cautela dei dati sensibili per requisito esplicito della roadmap tecnica |
| Dati relativi a incidenti di sicurezza | `incidents.data` (cifrato a riposo) | Descrizioni libere inserite dal cliente: possono occasionalmente contenere dati personali di terzi (es. "l'attacco ha esposto l'email del cliente X") — il cliente resta responsabile dei dati che inserisce in questo campo, CyberComplyIT li tratta come dati riservati per conto del cliente |
| Dati di conformità | `compliance_measures`, `assessment_results` | Stato di conformità alle 15 misure ACN e classificazione NIS2/CRA dell'organizzazione |
| Documenti generati | `documents.content`, PDF su storage locale | Contenuto generato dall'AI a partire dai dati dell'organizzazione (registro rischi, procedure, policy) |
| Dati di fatturazione | `subscriptions.stripe_customer_id`, `stripe_subscription_id` | Solo riferimenti/ID: i dati della carta di pagamento non transitano né sono mai salvati da CyberComplyIT, restano interamente su Stripe (PCI-DSS) |
| Log di audit | `audit_logs` (azione, entità, dettagli, indirizzo IP, timestamp) | Registro immutabile (solo insert), richiesto perché CyberComplyIT è essa stessa soggetta a NIS2 |

### 1.3 Finalità e base giuridica

| Finalità | Base giuridica (Art. 6 GDPR) |
|---|---|
| Erogazione del servizio (autenticazione, assessment, compliance tracker, documenti, incident reporting, supply chain) | Esecuzione di un contratto (Art. 6.1.b) |
| Fatturazione e gestione dell'abbonamento | Esecuzione di un contratto / obbligo legale (Art. 6.1.b, 6.1.c) |
| Email transazionali (conferma, notifiche di scadenza, alert di conformità) | Esecuzione di un contratto (Art. 6.1.b) |
| Audit log e sicurezza applicativa | Legittimo interesse del Titolare e obbligo normativo NIS2 (Art. 6.1.f, 6.1.c) |
| Comunicazioni di marketing | **Non implementate in piattaforma.** Se introdotte in futuro, richiederanno consenso esplicito separato (Art. 6.1.a) — nota per chi svilupperà quella funzionalità |

### 1.4 Destinatari e responsabili del trattamento (Art. 28)

| Fornitore | Ruolo | Dati trattati | Nota |
|---|---|---|---|
| Supabase | Autenticazione, database Postgres, storage | Tutti i dati della piattaforma | Richiede un Data Processing Agreement (DPA) firmato con Supabase prima del lancio commerciale; verificare la region del progetto (idealmente EU) |
| Stripe | Elaborazione pagamenti | Dati di fatturazione, non i dati della carta | Stripe è certificato PCI-DSS Livello 1; DPA disponibile nei termini standard di Stripe |
| Resend | Invio email transazionali | Indirizzo email, contenuto delle email inviate | Verificare i termini di trattamento dati di Resend prima di impostare una `RESEND_API_KEY` reale |
| Anthropic (Claude) | Generazione automatica del contenuto dei documenti di conformità | Risposte dell'assessment e dati aziendali usati come contesto per generare i documenti | **Da verificare con attenzione prima del lancio**: i prompt inviati a Claude includono dati aziendali del cliente (settore, dimensione, categoria NIS2). Va confermato che Anthropic offra garanzie adeguate per il trasferimento estero (SCC) e, se necessario, valutata l'opzione di non includere dati identificativi diretti nei prompt |

### 1.5 Trasferimenti extra-UE

Supabase, Stripe, Resend e Anthropic sono fornitori con infrastruttura (anche) fuori dall'UE.
Prima del lancio commerciale va verificato, per ciascuno, che il trasferimento sia coperto da
Clausole Contrattuali Standard (SCC) o altro meccanismo di trasferimento adeguato ai sensi del
Capo V GDPR — questo registro segnala il rischio ma non lo risolve: è un controllo legale, non
tecnico.

### 1.6 Misure di sicurezza tecniche e organizzative (Fase 8)

- Cifratura a riposo di P.IVA e dati incidente (Fernet, `app/db/encrypted_types.py`).
- Autenticazione e gestione password interamente delegate a Supabase Auth (nessuna password
  gestita direttamente da CyberComplyIT).
- Query parametrizzate ovunque (ORM SQLAlchemy, nessuna concatenazione di stringhe SQL).
- Header di sicurezza HTTP (CSP, HSTS, Permissions-Policy, no version disclosure),
  `robots.txt` che esclude le route autenticate.
- Rate limiting sul login (`SecurityHeadersMiddleware`, `slowapi`).
- Audit log immutabile (solo insert, conservato almeno 12 mesi) per ogni azione rilevante.
- Segreti solo in variabili d'ambiente, mai nel repository.
- Endpoint per l'esercizio dei diritti dell'interessato: `GET /gdpr/export` (Art. 20),
  `DELETE /gdpr/account` (Art. 17).

### 1.7 Tempi di conservazione

| Dato | Conservazione |
|---|---|
| Dati dell'account e dell'organizzazione | Per tutta la durata del contratto; cancellati su richiesta esplicita (`DELETE /gdpr/account`) o alla disdetta secondo la policy commerciale da definire |
| Audit log | Almeno 12 mesi, anche dopo la cancellazione dell'organizzazione a cui si riferivano (requisito Fase 8: i record non vengono mai cancellati, solo l'eventuale riferimento all'organizzazione cancellata viene azzerato) |
| Dati di fatturazione | Secondo i termini legali italiani sulla conservazione dei documenti fiscali (da confermare con il commercialista del Titolare: tipicamente 10 anni) |

### 1.8 Diritti dell'interessato

| Diritto | Come viene esercitato oggi |
|---|---|
| Accesso e portabilità (Art. 15, 20) | `GET /gdpr/export`, sezione "Privacy e dati" in Impostazioni > Profilo |
| Cancellazione (Art. 17) | `DELETE /gdpr/account`, sezione "Zona pericolosa" in Impostazioni > Profilo |
| Rettifica (Art. 16) | Modifica diretta dei propri dati dall'interfaccia (profilo, organizzazione) |
| Opposizione e limitazione (Art. 18, 21) | Non ancora un endpoint dedicato: da gestire via contatto diretto finché il volume di richieste non giustifica un'automazione |

## 2. Necessità del Data Protection Officer (DPO)

Non ancora deciso: è una valutazione che spetta al Titolare, non un'implementazione tecnica.
Gli elementi rilevanti per la decisione (Art. 37 GDPR):

- CyberComplyIT non effettua, per sua natura, un monitoraggio sistematico su larga scala di
  interessati, né tratta su larga scala le categorie particolari di dati dell'Art. 9.
- I dati potenzialmente più delicati (descrizioni di incidenti di sicurezza) sono trattati
  per conto dei clienti (che restano essi stessi Titolari dei dati che inseriscono), non
  costituiscono di per sé dati sensibili sistematicamente raccolti da CyberComplyIT sui propri
  interessati diretti (gli utenti che si registrano).
- Se il numero di clienti/organizzazioni dovesse crescere in modo significativo, o se
  CyberComplyIT iniziasse a trattare dati su scala più ampia per conto di clienti enterprise
  con requisiti contrattuali specifici, la valutazione andrebbe rifatta.

**Raccomandazione**: da confermare con un legale prima del lancio commerciale; allo stato
attuale (fase di sviluppo, nessun cliente reale) la nomina non risulta obbligatoria.

## 3. Cosa resta esplicitamente fuori da questo registro (compiti non tecnici)

- Privacy Policy e Cookie Policy pubblicate sul sito: **da scrivere con un avvocato**, non
  da un template (esplicitamente richiesto dalla roadmap tecnica). Questo registro fornisce
  la base fattuale (dati trattati, finalità, fornitori) da cui il legale può partire.
- Firma dei DPA (Data Processing Agreement) con Supabase, Stripe, Resend, Anthropic.
- Verifica del meccanismo di trasferimento extra-UE per ciascun fornitore (§1.5).
- Decisione formale sulla nomina di un DPO (§2).
- GitHub Secret Scanning: attivabile solo dopo che il repository sarà stato pubblicato su un
  vero account GitHub (non ancora avvenuto in questa sessione di sviluppo).
