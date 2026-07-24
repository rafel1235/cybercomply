import Link from "next/link";

export const metadata = {
  title: "Privacy Policy — CyberComplyIT",
};

/** Bozza in attesa di revisione legale (Fase 8/11 della roadmap tecnica richiedono che la
 * Privacy Policy definitiva sia redatta "con un avvocato, non template"): questa pagina
 * esiste perché il footer e la Cookie Policy la referenziano già, ed evita un link rotto,
 * ma NON è il testo legale definitivo. Descrive onestamente, come il Registro dei
 * Trattamenti (docs/REGISTRO_TRATTAMENTI.md), i trattamenti che la piattaforma svolge
 * realmente secondo il proprio modello dati e le integrazioni effettivamente configurate. */
export default function PrivacyPolicyPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-16">
      <Link href="/" className="text-sm text-brand-blue underline">
        ← Torna alla home
      </Link>
      <h1 className="text-2xl font-bold text-brand-dark">Privacy Policy</h1>

      <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
        Bozza in attesa di revisione legale: questo testo descrive onestamente i trattamenti dati
        effettivamente svolti dalla piattaforma, ma non sostituisce una Privacy Policy redatta da un
        avvocato prima del lancio commerciale (vedi docs/REGISTRO_TRATTAMENTI.md per il dettaglio
        tecnico completo).
      </p>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Titolare del trattamento</h2>
        <p className="text-slate-700">
          CyberComplyIT è il titolare del trattamento dei dati personali raccolti tramite questa
          piattaforma. Sede legale e dati di contatto societari verranno pubblicati qui prima del
          lancio commerciale.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Quali dati trattiamo</h2>
        <p className="text-slate-700">
          Trattiamo i dati identificativi e di contatto dell&apos;account (nome, email), i dati
          aziendali che inserisci per l&apos;assessment di conformità (settore, dimensione, P.IVA),
          i dati relativi a incidenti di sicurezza che registri, lo stato di conformità alle misure
          NIS2/CRA, i documenti generati con l&apos;AI e i riferimenti di fatturazione (mai i dati
          della carta di pagamento, che restano esclusivamente su Stripe).
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Perché trattiamo questi dati</h2>
        <p className="text-slate-700">
          Per erogare il servizio che hai richiesto (esecuzione del contratto): assessment,
          compliance tracker, incident reporting, supply chain risk e generazione documenti. I dati
          di fatturazione sono trattati per adempiere agli obblighi contrattuali e fiscali.
          L&apos;audit log è trattato per legittimo interesse e per obbligo normativo, dato che
          CyberComplyIT è essa stessa soggetta a NIS2.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Con chi condividiamo i dati</h2>
        <p className="text-slate-700">
          Ci appoggiamo a fornitori terzi che agiscono come responsabili del trattamento: Supabase
          (autenticazione e database), Stripe (pagamenti, certificato PCI-DSS), Resend (invio email
          transazionali) e Anthropic (generazione AI dei documenti di conformità, a partire dai dati
          aziendali che inserisci). Non vendiamo né cediamo i tuoi dati a terzi per finalità di
          marketing.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">I tuoi diritti</h2>
        <p className="text-slate-700">
          Puoi esportare tutti i tuoi dati in qualsiasi momento dalle impostazioni del profilo
          (diritto di portabilità, Art. 20 GDPR) e richiedere la cancellazione completa del tuo
          account e dei tuoi dati, con effetto entro 30 giorni (diritto alla cancellazione, Art. 17
          GDPR).
        </p>
      </section>

      <p className="text-xs text-slate-500">
        Per l&apos;informativa specifica sui cookie, consulta la{" "}
        <Link href="/cookie-policy" className="underline">
          Cookie Policy
        </Link>
        .
      </p>
    </main>
  );
}
