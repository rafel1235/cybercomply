import Link from "next/link";

/**
 * Landing page minimale. I contenuti completi (pricing dettagliato, FAQ, sezioni marketing)
 * arrivano in Fase 4/11; qui c'è la struttura essenziale richiesta dalla roadmap (Fase 4:
 * "Landing page con descrizione prodotto, pricing, CTA 'Inizia gratis'").
 */
export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-8 px-6 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-blue">
        NIS2 · Cyber Resilience Act · D.Lgs. 138/2024
      </p>
      <h1 className="text-4xl font-bold text-brand-dark sm:text-5xl">
        CyberComply<span className="text-brand-amber">IT</span>
      </h1>
      <p className="max-w-2xl text-lg text-slate-600">
        La piattaforma italiana che aiuta le PMI ad adeguarsi a NIS2 e al Cyber Resilience Act:
        assessment guidato, compliance tracker, incident reporting e supply chain risk, con
        documentazione generata su misura per la tua azienda.
      </p>
      <div className="flex gap-4">
        <Link
          href="/register"
          className="rounded-md bg-brand-blue px-6 py-3 font-semibold text-white hover:bg-brand-dark"
        >
          Inizia gratis
        </Link>
        <Link
          href="/login"
          className="rounded-md border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-100"
        >
          Accedi
        </Link>
      </div>
    </main>
  );
}
