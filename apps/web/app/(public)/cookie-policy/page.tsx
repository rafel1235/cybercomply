import Link from "next/link";

export const metadata = {
  title: "Informativa sui cookie — CyberComplyIT",
};

/** Informativa onesta basata su ciò che la piattaforma fa davvero (Fase 8 — GDPR),
 * non un template generico: nessuna libreria di analytics/tracciamento è installata
 * (vedi package.json), l'unico cookie impostato è quello di sessione di Supabase Auth,
 * strettamente necessario per il funzionamento del servizio e quindi esente dall'obbligo
 * di consenso preventivo secondo le linee guida del Garante Privacy sui cookie tecnici. */
export default function CookiePolicyPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-16">
      <Link href="/login" className="text-sm text-brand-blue underline">
        ← Torna al login
      </Link>
      <h1 className="text-2xl font-bold text-brand-dark">Informativa sui cookie</h1>

      <p className="text-slate-700">
        CyberComplyIT utilizza un solo cookie, strettamente necessario per il funzionamento del
        servizio: quello di sessione impostato da Supabase Auth (il nostro fornitore di
        autenticazione) per riconoscere che sei autenticato e mantenerti connesso tra una pagina e
        l&apos;altra.
      </p>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">
          Perché non c&apos;è un banner di consenso
        </h2>
        <p className="text-slate-700">
          Non utilizziamo cookie di profilazione, analytics o pubblicitari di alcun tipo: nessun
          Google Analytics, nessun pixel pubblicitario, nessuno strumento di tracciamento di terze
          parti. Il cookie di sessione rientra nella categoria dei &quot;cookie tecnici&quot;
          secondo le linee guida del Garante per la protezione dei dati personali: è indispensabile
          per erogare il servizio che hai richiesto (restare autenticato) e per questo è esente
          dall&apos;obbligo di consenso preventivo previsto per i cookie di profilazione.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Cookie utilizzato</h2>
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-300">
              <th className="py-2 pr-4 font-semibold">Nome</th>
              <th className="py-2 pr-4 font-semibold">Impostato da</th>
              <th className="py-2 pr-4 font-semibold">Finalità</th>
              <th className="py-2 font-semibold">Durata</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-100">
              <td className="py-2 pr-4">sb-*-auth-token</td>
              <td className="py-2 pr-4">Supabase Auth (tecnico, prima parte)</td>
              <td className="py-2 pr-4">Mantenere la sessione di accesso autenticata</td>
              <td className="py-2">Fino al logout o alla scadenza della sessione</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">Pagamenti (Stripe)</h2>
        <p className="text-slate-700">
          Se attivi o gestisci un abbonamento, vieni reindirizzato alle pagine sicure di Stripe
          (checkout.stripe.com), che non fanno parte del nostro sito: Stripe potrà impostare propri
          cookie secondo la propria informativa, di cui non siamo titolari. Non carichiamo mai
          script o cookie di Stripe sul nostro dominio.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-brand-dark">
          Come gestire o rimuovere questo cookie
        </h2>
        <p className="text-slate-700">
          Puoi cancellare il cookie di sessione in qualsiasi momento dalle impostazioni del tuo
          browser: l&apos;effetto sarà semplicemente la disconnessione dal servizio, che dovrai poi
          rieffettuare per continuare a usarlo.
        </p>
      </section>

      <p className="text-xs text-slate-500">
        Questa pagina descrive esclusivamente i cookie. Per l&apos;informativa completa sul
        trattamento dei dati personali, consulta la{" "}
        <Link href="/privacy-policy" className="underline">
          Privacy Policy
        </Link>
        .
      </p>
    </main>
  );
}
