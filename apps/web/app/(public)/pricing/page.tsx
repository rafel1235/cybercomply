import Link from "next/link";
import { Footer } from "@/components/marketing/Footer";
import {
  PLAN_FEATURES,
  PLAN_LABELS,
  PLAN_ORDER,
  PLAN_PRICE_LABELS,
  PLAN_PURCHASABLE,
  PLAN_TAGLINES,
} from "@/lib/planLabels";

export const metadata = {
  title: "Prezzi — CyberComplyIT",
  description:
    "Confronta i piani CyberComplyIT: Free, Essential, Business ed Enterprise per la conformità NIS2 e Cyber Resilience Act.",
};

/** Pagina pricing pubblica (Fase 4 — roadmap: "Pagina pricing con dettaglio piani").
 * Riusa la stessa fonte dati di settings/billing/page.tsx (lib/planLabels.ts) per non
 * disallineare mai i prezzi mostrati qui da quelli mostrati agli utenti già registrati. */
export default function PricingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-10 px-6 py-16">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-3xl font-bold text-brand-dark sm:text-4xl">Prezzi</h1>
        <p className="max-w-2xl text-slate-600">
          Scegli il piano adatto alla tua azienda. Nessuna carta di credito richiesta per iniziare:
          puoi provare Essential gratis, oppure restare su Free senza scadenza.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PLAN_ORDER.map((plan) => {
          const purchasable = PLAN_PURCHASABLE[plan];
          return (
            <div
              key={plan}
              className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-5"
            >
              <p className="text-lg font-bold text-brand-dark">{PLAN_LABELS[plan]}</p>
              <p className="text-2xl font-bold text-brand-dark">{PLAN_PRICE_LABELS[plan]}</p>
              <p className="text-sm text-slate-500">{PLAN_TAGLINES[plan]}</p>
              <ul className="flex flex-col gap-1.5 text-sm text-slate-600">
                {PLAN_FEATURES[plan].map((feature) => (
                  <li key={feature} className="flex gap-2">
                    <span className="text-brand-blue">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>
              {purchasable ? (
                <Link
                  href="/register"
                  className="mt-auto rounded-md bg-brand-blue px-4 py-2 text-center text-sm font-semibold text-white hover:bg-brand-blue/90"
                >
                  Inizia gratis
                </Link>
              ) : plan === "enterprise" ? (
                <a
                  href="mailto:info@cybercomplyit.it?subject=Richiesta%20piano%20Enterprise"
                  className="mt-auto rounded-md border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Contattaci
                </a>
              ) : (
                <Link
                  href="/register"
                  className="mt-auto rounded-md border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Inizia gratis
                </Link>
              )}
            </div>
          );
        })}
      </div>

      <Footer />
    </main>
  );
}
