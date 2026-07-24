"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { createClient } from "@/lib/supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function ConfirmEmailPage() {
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) {
        setStatus("error");
        return;
      }

      // Fase 7: questo è il vero primo punto in cui l'utente ha una sessione dopo la
      // registrazione — prima d'ora /auth/sync veniva chiamato solo al login successivo,
      // quindi chi confermava l'email e andava dritto in dashboard non aveva ancora
      // un'organizzazione creata. I metadati (nome azienda, nome completo, eventuale
      // token di invito) sono quelli salvati da register/page.tsx al momento della
      // registrazione su Supabase.
      const metadata = data.session.user.user_metadata ?? {};
      try {
        await fetch(`${API_BASE_URL}/auth/sync`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${data.session.access_token}`,
          },
          body: JSON.stringify({
            full_name: metadata.full_name ?? undefined,
            organization_name: metadata.organization_name ?? undefined,
            invite_token: metadata.invite_token ?? undefined,
          }),
        });
      } catch {
        // Non blocca l'accesso: se il backend non risponde ora, il prossimo login lo
        // riprova (stesso comportamento già esistente in login.tsx).
      }

      setStatus("ok");
    });
  }, []);

  return (
    <AuthLayout title="Conferma email">
      {status === "checking" && <p className="text-slate-600">Verifica in corso…</p>}
      {status === "ok" && (
        <div className="flex flex-col gap-3">
          <p className="text-slate-600">Email confermata. Il tuo account è attivo.</p>
          <Link
            href="/dashboard"
            className="rounded-md bg-brand-blue px-4 py-2 text-center font-semibold text-white"
          >
            Vai alla dashboard
          </Link>
        </div>
      )}
      {status === "error" && (
        <div className="flex flex-col gap-3">
          <p className="text-slate-600">
            Il link non è valido o è scaduto. Prova ad accedere di nuovo.
          </p>
          <Link href="/login" className="text-brand-blue underline">
            Torna al login
          </Link>
        </div>
      )}
    </AuthLayout>
  );
}
