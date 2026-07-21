"use client";

import { useState } from "react";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Field } from "@/components/auth/Field";
import { createClient } from "@/lib/supabase/client";

export default function RegisterPage() {
  const supabase = createClient();

  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, organization_name: organizationName },
        emailRedirectTo: `${window.location.origin}/confirm`,
      },
    });

    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    setSubmitted(true);
  }

  if (submitted) {
    return (
      <AuthLayout title="Controlla la tua email">
        <p className="text-slate-600">
          Ti abbiamo inviato un link di conferma a <strong>{email}</strong>. Clicca sul link per
          attivare l&apos;account e accedere alla piattaforma.
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Crea il tuo account CyberComplyIT">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Field label="Nome e cognome" value={fullName} onChange={setFullName} required />
        <Field
          label="Nome azienda"
          value={organizationName}
          onChange={setOrganizationName}
          required
        />
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          required
          minLength={8}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brand-blue px-4 py-2 font-semibold text-white disabled:opacity-60"
        >
          {loading ? "Creazione account…" : "Crea account gratis"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        Hai già un account?{" "}
        <Link href="/login" className="text-brand-blue underline">
          Accedi
        </Link>
      </p>
    </AuthLayout>
  );
}
