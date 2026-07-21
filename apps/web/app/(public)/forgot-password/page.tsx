"use client";

import { useState } from "react";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Field } from "@/components/auth/Field";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    setLoading(false);

    if (resetError) {
      setError(resetError.message);
      return;
    }
    setSent(true);
  }

  if (sent) {
    return (
      <AuthLayout title="Controlla la tua email">
        <p className="text-slate-600">
          Se esiste un account per <strong>{email}</strong>, riceverai un link per reimpostare la
          password.
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Password dimenticata">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brand-blue px-4 py-2 font-semibold text-white disabled:opacity-60"
        >
          {loading ? "Invio…" : "Invia link di reset"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        <Link href="/login" className="text-brand-blue underline">
          Torna al login
        </Link>
      </p>
    </AuthLayout>
  );
}
