"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-3xl font-bold text-brand-dark">Qualcosa è andato storto</h1>
      <p className="text-slate-600">
        Si è verificato un errore imprevisto. Il team è stato notificato automaticamente.
      </p>
      <button
        onClick={reset}
        className="rounded-md bg-brand-blue px-4 py-2 font-semibold text-white"
      >
        Riprova
      </button>
    </main>
  );
}
