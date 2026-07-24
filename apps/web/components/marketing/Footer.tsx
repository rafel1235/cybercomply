import Link from "next/link";

/** Footer per le pagine pubbliche di marketing (landing, pricing), richiesto da Fase 4
 * della roadmap tecnica: "Footer con: Privacy Policy, Cookie Policy, Termini di servizio,
 * Contatti, P.IVA". Privacy Policy e Termini di servizio sono bozze in attesa di revisione
 * legale (vedi le rispettive pagine): non è stato inventato un testo legale definitivo, in
 * coerenza con l'approccio già usato per la Cookie Policy e il Registro dei Trattamenti. */
export function Footer() {
  return (
    <footer className="mx-auto flex w-full max-w-5xl flex-col gap-3 border-t border-slate-200 px-6 py-8 text-sm text-slate-500">
      <nav className="flex flex-wrap gap-x-6 gap-y-2">
        <Link href="/privacy-policy" className="underline hover:text-slate-700">
          Privacy Policy
        </Link>
        <Link href="/cookie-policy" className="underline hover:text-slate-700">
          Cookie Policy
        </Link>
        <Link href="/termini-di-servizio" className="underline hover:text-slate-700">
          Termini di servizio
        </Link>
        <a href="mailto:info@cybercomplyit.it" className="underline hover:text-slate-700">
          Contatti
        </a>
      </nav>
      <p className="text-xs text-slate-400">
        CyberComplyIT — P.IVA: [da inserire] · info@cybercomplyit.it
      </p>
    </footer>
  );
}
