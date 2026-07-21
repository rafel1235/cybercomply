import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-3xl font-bold text-brand-dark">Pagina non trovata</h1>
      <p className="text-slate-600">La pagina che cerchi non esiste o è stata spostata.</p>
      <Link href="/" className="text-brand-blue underline">
        Torna alla home
      </Link>
    </main>
  );
}
