# Accessibilità — WCAG AA (Fase 10)

## Navigabilità da tastiera

Verificato che ogni elemento interattivo dell'app sia un elemento HTML nativo
(`<button>`, `<a>`/`<Link>`, `<input>`, `<select>`, `<textarea>`) — tutti focalizzabili e
azionabili da tastiera per costruzione, senza bisogno di `tabIndex`/gestori di eventi
tastiera aggiuntivi. Cercato esplicitamente elementi non nativi con `onClick` (es.
`<div onClick=...>`, un pattern comune che rompe la navigazione da tastiera): nessuno
trovato in tutto `apps/web`. Nessuna libreria di componenti UI custom (dropdown, modali)
che potrebbe introdurre un simile problema.

**Bug reale corretto**: i pulsanti-filtro di stato in `dashboard/incidents/page.tsx`
(Tutti/Aperti/Chiusi/...) comunicavano lo stato selezionato solo con un colore di sfondo
diverso — un utente di screen reader non aveva modo di sapere quale filtro fosse attivo.
Aggiunto `aria-pressed={statusFilter === value}` su ciascun pulsante e
`role="group" aria-label="Filtra per stato"` sul contenitore.

## Indicatore di focus visibile

Tutti i campi di input (`focus:outline-none` — necessario per sostituire l'outline nativo
del browser con uno stile coerente col brand) avevano come unico indicatore di focus un
cambio di colore del bordo (`focus:border-brand-blue`), un segnale debole per utenti con
bassa vista. Aggiunto `focus:ring-2 focus:ring-brand-blue/30` su tutti i 12 campi
interessati (form di autenticazione, assessment, incidenti, fornitori, team, note di
conformità): l'indicatore di focus ora è un anello visibile attorno al campo, non solo un
bordo più scuro.

## `aria-label` sui controlli senza testo visibile associato

Nessun pulsante icona-soltanto esiste nell'app (nessuna libreria di icone in
`package.json`, tutti i pulsanti hanno testo visibile) — il caso classico "bottoni senza
testo" della roadmap non si presenta qui. È emerso però un problema equivalente su
**controlli di form senza alcuna etichetta associata** (select di filtro, textarea di
note, input di ricerca) che si affidavano solo alla posizione visiva o, nel peggiore dei
casi, al solo placeholder — esattamente l'anti-pattern segnalato dalla roadmap ("form con
label associate correttamente, non placeholder come sostituto"). Corretti con
`aria-label` (dove un'etichetta visibile avrebbe appesantito un filtro compatto) su:

- `dashboard/compliance/page.tsx`: filtro categoria, filtro stato, select di stato per
  singola misura (etichettato con il nome della misura, per distinguere le righe), select
  del tipo di documento da generare, textarea delle note (idem, per misura)
- `dashboard/suppliers/page.tsx`: select di criticità per singolo fornitore
- `dashboard/incidents/page.tsx`: campo di ricerca (prima solo `placeholder`)
- `settings/team/page.tsx`: campo email e select di ruolo del modulo di invito

Tutti gli altri form dell'app (login, registrazione, recupero password, assessment,
creazione incidente/fornitore, questionario pubblico) avvolgevano già correttamente ogni
campo in un `<label>` nativo (associazione implicita) — verificato file per file, nessuna
modifica necessaria lì.

## Messaggi di stato dinamici (toast)

Il sistema di notifiche (`lib/toast.tsx`) mostrava e nascondeva i messaggi di
successo/errore senza mai spostare il focus né annunciarli — un utente di screen reader
non veniva mai informato dell'esito di un'azione (WCAG 4.1.3, "Status Messages").
Aggiunto `role="alert"` (implica `aria-live="assertive"`, annuncio immediato) per i toast
di errore e `role="status"` (`aria-live="polite"`) per successo/info.

## Contrasto colori (WCAG AA — 4.5:1 per testo normale)

Analizzato ogni colore di testo usato nell'app contro il proprio sfondo. Trovato un
problema reale e diffuso: `text-slate-400` (`#94a3b8`) su sfondo bianco ha un rapporto di
contrasto di circa **2.6:1** — ben sotto la soglia minima di 4.5:1 richiesta per il testo
normale — eppure era la classe usata per quasi tutti i testi secondari dell'app (date,
etichette di metadati, stati vuoti, note a piè di pagina) in 14 file diversi. Sostituito
ovunque con `text-slate-500` (`#64748b`), che misura **~4.76:1** contro bianco — passa
WCAG AA con margine. Le uniche istanze di `text-slate-400` rimaste (in due `disabled:`
su campi di form disabilitati) sono state anch'esse aggiornate a `text-slate-500` per
coerenza, pur non essendo un requisito WCAG (il testo di un componente disattivato è
esplicitamente escluso dal criterio 1.4.3).

Verificati anche gli altri abbinamenti colore/sfondo dell'app (badge di stato
`green-800`/`amber-800`/`red-800`/`slate-700` su tinte chiare corrispondenti, pulsanti
`text-white` su `bg-brand-blue` — contrasto ~5.18:1, link `text-brand-blue` su bianco —
stesso valore): tutti già conformi, nessuna altra modifica necessaria.

## Bug reale scoperto e corretto: link interni come `<a>` invece di `next/link`

Non strettamente un problema di accessibilità in senso stretto, ma correlato: 5
collegamenti verso `/settings/billing` erano scritti come `<a href="...">` invece di
`<Link href="...">` (vedi `docs/PERFORMANCE.md`), il che tra l'altro impedisce anche la
gestione automatica del focus da parte di Next.js dopo una navigazione lato client (Next
sposta il focus sull'elemento `<h1>` della pagina di destinazione dopo un `Link`, non
dopo un `<a>` con reload completo, ma in quel caso il browser ripristina comunque il
focus di default all'inizio del documento — nessuna regressione, solo un'esperienza meno
fluida). Corretti come parte del lavoro di performance.

## Cosa NON è stato verificato in questa sessione

Nessun test reale con screen reader (VoiceOver su macOS o NVDA su Windows, richiesti
esplicitamente dalla roadmap) è stato eseguito: richiede un sistema operativo reale con
screen reader installato, non disponibile in questo ambiente sandbox Linux. Le correzioni
sopra (label, `aria-label`, `role`, focus visibile, contrasto) sono basate sull'analisi
statica del markup e sui criteri WCAG 2.1 AA, non su un ascolto reale con uno screen
reader. Da fare prima del lancio commerciale, come richiesto dalla roadmap.

Nessun test automatico di accessibilità (es. `axe-core`, `jest-axe`, Lighthouse
Accessibility audit) è stato eseguito: Lighthouse non è disponibile in questo ambiente
(vedi `docs/PERFORMANCE.md`), e non è stata aggiunta una nuova dipendenza (`@axe-core/react`
o simili) per non allargare il perimetro di questa fase oltre le correzioni già
individuate manualmente.
