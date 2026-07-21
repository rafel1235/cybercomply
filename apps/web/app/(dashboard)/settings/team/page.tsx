"use client";

import { useEffect, useState } from "react";
import { Field } from "@/components/auth/Field";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function TeamSettingsPage() {
  const supabase = createClient();
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const { data } = await supabase.auth.getSession();
      if (!data.session) return;
      try {
        const me = await apiFetch("/auth/me", data.session.access_token);
        setOrganizationId(me.organizations?.[0]?.id ?? null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [supabase]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    const { data } = await supabase.auth.getSession();
    if (!data.session || !organizationId) return;

    try {
      await apiFetch(
        `/auth/organizations/${organizationId}/invites`,
        data.session.access_token,
        {
          method: "POST",
          body: JSON.stringify({ email: inviteEmail, role: "viewer" }),
        }
      );
      setMessage(
        `Invito creato per ${inviteEmail}. L'invio dell'email arriverà con la Fase 7 ` +
          "(provider email transazionale): per ora l'invito è salvato e pronto."
      );
      setInviteEmail("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Errore durante l'invito.");
    }
  }

  if (loading) {
    return <p className="text-slate-500">Caricamento…</p>;
  }

  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="text-2xl font-bold text-brand-dark">Membri del team</h1>
      <form onSubmit={handleInvite} className="flex flex-col gap-3">
        <Field
          label="Email collaboratore"
          type="email"
          value={inviteEmail}
          onChange={setInviteEmail}
          required
        />
        {message && <p className="rounded-md bg-slate-100 px-3 py-2 text-sm">{message}</p>}
        <button
          type="submit"
          className="w-fit rounded-md bg-brand-blue px-4 py-2 font-semibold text-white"
        >
          Invita come Viewer
        </button>
      </form>
    </div>
  );
}
