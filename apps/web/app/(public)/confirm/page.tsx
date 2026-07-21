"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { createClient } from "@/lib/supabase/client";

export default function ConfirmEmailPage() {
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      setStatus(data.session ? "ok" : "error");
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
