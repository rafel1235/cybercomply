import Link from "next/link";

/** Stato "bloccato dal piano" mostrato al posto del contenuto normale quando un modulo
 * risponde 403 perché non incluso nel piano attivo (Fase 6): stesso posto visivo
 * dell'EmptyState, ma con un invito chiaro all'upgrade invece di far pensare a un errore
 * o a "nessun dato ancora". */
export function UpsellNotice({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-brand-amber/40 bg-amber-50 p-10 text-center">
      <p className="font-medium text-brand-dark">{title}</p>
      <p className="max-w-sm text-sm text-slate-600">{description}</p>
      <Link
        href="/settings/billing"
        className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
      >
        Vedi i piani
      </Link>
    </div>
  );
}
