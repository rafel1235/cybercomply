import Link from "next/link";

export const metadata = {
  title: "Termini di servizio — CyberComplyIT",
};

/** Bozza in attesa di revisione legale, stesso approccio della Privacy Policy: la roadmap
 * (Fase 11) richiede termini di servizio redatti con un avvocato prima del lancio. Questa
 * pagina evita un link rotto dal footer e descrive onestamente le condizioni d'uso di base
 * già implementate nel prodotto (piani, fatturazione, disclaimer), ma non è il testo legale
 * definitivo. */
export default function TerminiDiServizioPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-16">
      <Link href="/" className="text-sm text-brand-blue underline">
        ← Torna alla home
      </Link>
      <h1 className="text-2xl font-bold text-brand-dark">Termini di servizio</h1>

      <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
        Bozza in attesa di revisione legale: non sostituisce termini di servizio redatti da un
        avvocato prima del lancio commerciale.
      </p>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Il servizio</h2>
        <p className="text-slate-700">
          CyberComplyIT è una piattaforma SaaS che aiuta le PMI italiane a valutare e tracciare la
          propria conformità a NIS2 e al Cyber Resilience Act: assessment guidato, compliance
          tracker, incident reporting, supply chain risk e generazione automatica di documenti di
          conformità tramite intelligenza artificiale.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Disclaimer</h2>
        <p className="text-slate-700">
          CyberComplyIT non sostituisce una consulenza legale o di cybersecurity specializzata. I
          documenti generati dall&apos;AI sono un supporto operativo basato sui dati che fornisci:
          la responsabilità di verificarne l&apos;adeguatezza al caso specifico e di ottenere
          consulenza professionale dove necessario resta dell&apos;utente.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Piani e fatturazione</h2>
        <p className="text-slate-700">
          I dettagli di ciascun piano (limiti di utenti, documenti generabili, funzionalità incluse)
          sono descritti nella pagina{" "}
          <Link href="/pricing" className="underline">
            Prezzi
          </Link>
          . I pagamenti sono elaborati da Stripe; puoi gestire o annullare il tuo abbonamento in
          qualsiasi momento dal portale abbonamento raggiungibile dalle impostazioni di
          fatturazione.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Il tuo account</h2>
        <p className="text-slate-700">
          Sei responsabile della riservatezza delle tue credenziali di accesso e
          dell&apos;accuratezza dei dati aziendali che inserisci. Puoi esportare o cancellare
          definitivamente i tuoi dati in qualsiasi momento dalle impostazioni del profilo.
        </p>
      </section>

      <p className="text-xs text-slate-500">
        Per il trattamento dei dati personali, consulta la{" "}
        <Link href="/privacy-policy" className="underline">
          Privacy Policy
        </Link>
        .
      </p>
    </main>
  );
}
