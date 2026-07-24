"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Field } from "@/components/auth/Field";
import { createClient } from "@/lib/supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();
  const sessionExpired = searchParams.get("expired") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function reportLoginEvent(success: boolean) {
    try {
      await fetch(`${API_BASE_URL}/auth/login-events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, success }),
      });
    } catch {
      // Il tracciamento del tentativo di login non deve mai bloccare l'utente:
      // se l'API non risponde, il login prosegue comunque lato Supabase.
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    await reportLoginEvent(!signInError);

    if (signInError) {
      setLoading(false);
      setError(signInError.message);
      return;
    }

    // Sincronizza l'utente nel backend (crea organizzazione alla primissima volta).
    if (data.session) {
      const syncResponse = await fetch(`${API_BASE_URL}/auth/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${data.session.access_token}`,
        },
        body: JSON.stringify({}),
      }).catch(() => null);

      // Bug reale corretto (Fase 10 — audit finale): l'account può risultare "bloccato"
      // lato nostro backend (troppi tentativi falliti) anche se Supabase ha appena
      // autenticato con successo — Supabase non sa nulla del nostro blocco. Prima di
      // questa correzione l'utente veniva comunque mandato in dashboard, dove ogni
      // chiamata avrebbe iniziato a fallire silenziosamente con 423. Ora il logout è
      // esplicito e l'errore è chiaro.
      if (syncResponse && syncResponse.status === 423) {
        await supabase.auth.signOut();
        setLoading(false);
        setError(
          "Account temporaneamente bloccato per troppi tentativi di accesso falliti. Riprova tra qualche minuto."
        );
        return;
      }
    }

    setLoading(false);
    router.push("/dashboard");
  }

  return (
    <AuthLayout title="Accedi a CyberComplyIT">
      {sessionExpired && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          La tua sessione è scaduta. Accedi di nuovo per continuare.
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        <Field label="Password" type="password" value={password} onChange={setPassword} required />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brand-blue px-4 py-2 font-semibold text-white disabled:opacity-60"
        >
          {loading ? "Accesso…" : "Accedi"}
        </button>
      </form>
      <div className="mt-4 flex justify-between text-sm text-slate-600">
        <Link href="/forgot-password" className="text-brand-blue underline">
          Password dimenticata?
        </Link>
        <Link href="/register" className="text-brand-blue underline">
          Crea un account
        </Link>
      </div>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
