"use client";

import { useEffect, useState } from "react";
import { Field } from "@/components/auth/Field";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function OrganizationSettingsPage() {
  const supabase = createClient();
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const { data } = await supabase.auth.getSession();
      if (!data.session) return;
      try {
        const me = await apiFetch("/auth/me", data.session.access_token);
        const org = me.organizations?.[0];
        if (org) {
          setOrganizationId(org.id);
          setName(org.name ?? "");
          setSector(org.sector ?? "");
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [supabase]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setMessage(
      "Il salvataggio delle modifiche ai dati organizzazione (PUT /organization) arriva " +
        "in Fase 3 (API complete): per ora questa pagina mostra i dati sincronizzati alla registrazione."
    );
  }

  if (loading) {
    return <p className="text-slate-500">Caricamento…</p>;
  }

  if (!organizationId) {
    return <p className="text-slate-500">Nessuna organizzazione associata al tuo account.</p>;
  }

  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="text-2xl font-bold text-brand-dark">Impostazioni organizzazione</h1>
      <form onSubmit={handleSave} className="flex flex-col gap-3">
        <Field label="Nome azienda" value={name} onChange={setName} required />
        <Field label="Settore" value={sector} onChange={setSector} />
        {message && <p className="rounded-md bg-slate-100 px-3 py-2 text-sm">{message}</p>}
        <button
          type="submit"
          className="w-fit rounded-md bg-brand-blue px-4 py-2 font-semibold text-white"
        >
          Salva
        </button>
      </form>
    </div>
  );
}
