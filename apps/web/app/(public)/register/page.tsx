"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Field } from "@/components/auth/Field";
import { createClient } from "@/lib/supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ROLE_LABELS: Record<string, string> = { admin: "Amministratore", viewer: "Viewer" };

interface InvitePreview {
  organization_name: string;
  invited_email: string;
  role: string;
  valid: boolean;
  reason: string | null;
}

export default function RegisterPage() {
  const supabase = createClient();

  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  // Token di invito letto solo lato client dopo il mount (come già fatto altrove per
  // parametri non essenziali al primo render): se presente, la registrazione unisce
  // l'utente all'organizzazione dell'invito invece di crearne una nuova.
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [invite, setInvite] = useState<InvitePreview | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("invite");
    if (!token) return;
    setInviteToken(token);
    setInviteLoading(true);
    fetch(`${API_BASE_URL}/public/invites/${token}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: InvitePreview | null) => {
        if (data) {
          setInvite(data);
          if (data.valid) {
            setEmail(data.invited_email);
          }
        }
      })
      .catch(() => null)
      .finally(() => setInviteLoading(false));
  }, []);

  const joiningValidInvite = Boolean(invite?.valid);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
          organization_name: joiningValidInvite ? undefined : organizationName,
          invite_token: joiningValidInvite ? inviteToken : undefined,
        },
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
      {inviteLoading && <p className="text-sm text-slate-500">Verifica invito…</p>}
      {invite && joiningValidInvite && (
        <p className="rounded-md bg-brand-blue/10 p-3 text-sm text-brand-dark">
          Stai per unirti a <strong>{invite.organization_name}</strong> come{" "}
          {ROLE_LABELS[invite.role] ?? invite.role}.
        </p>
      )}
      {invite && !invite.valid && (
        <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          {invite.reason ?? "Questo invito non è più valido."} Puoi comunque creare un account
          separato qui sotto.
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Field label="Nome e cognome" value={fullName} onChange={setFullName} required />
        {!joiningValidInvite && (
          <Field
            label="Nome azienda"
            value={organizationName}
            onChange={setOrganizationName}
            required
          />
        )}
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          required
          disabled={joiningValidInvite}
        />
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
