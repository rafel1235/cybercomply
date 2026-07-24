import Link from "next/link";

export function AuthLayout({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6">
      <h1 className="text-2xl font-bold text-brand-dark">{title}</h1>
      {children}
      <p className="text-center text-xs text-slate-500">
        <Link href="/cookie-policy" className="underline">
          Informativa sui cookie
        </Link>
      </p>
    </main>
  );
}
