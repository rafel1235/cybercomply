import Link from "next/link";
import { Footer } from "@/components/marketing/Footer";

/**
 * Landing page (Fase 4 — roadmap: "Landing page con descrizione prodotto, pricing, CTA
 * 'Inizia gratis'"). Il dettaglio dei piani vive nella pagina /pricing dedicata (stessa
 * fonte dati di settings/billing, lib/planLabels.ts) per non duplicare i prezzi in due
 * posti: qui c'è solo un rimando diretto. FAQ, video walkthrough e altri contenuti di
 * marketing più ampi restano Fase 11 (fuori dall'ambito di questo audit Fase 0-10).
 */
export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <main className="mx-auto flex flex-1 w-full max-w-5xl flex-col items-center justify-center gap-8 px-6 text-center">
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
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/register"
            className="rounded-md bg-brand-blue px-6 py-3 font-semibold text-white hover:bg-brand-dark"
          >
            Inizia gratis
          </Link>
          <Link
            href="/pricing"
            className="rounded-md border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-100"
          >
            Vedi i prezzi
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-100"
          >
            Accedi
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
