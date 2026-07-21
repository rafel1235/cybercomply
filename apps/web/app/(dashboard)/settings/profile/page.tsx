"use client";

import { useEffect, useState } from "react";
import { Field } from "@/components/auth/Field";
import { createClient } from "@/lib/supabase/client";

export default function ProfileSettingsPage() {
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? "");
      setFullName((data.user?.user_metadata?.full_name as string) ?? "");
    });
  }, [supabase]);

  async function handleSaveName(e: React.FormEvent) {
    e.preventDefault();
    const { error } = await supabase.auth.updateUser({ data: { full_name: fullName } });
    setMessage(error ? error.message : "Nome aggiornato.");
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) {
      setMessage("La password deve avere almeno 8 caratteri.");
      return;
    }
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    setMessage(error ? error.message : "Password aggiornata.");
    setNewPassword("");
  }

  return (
    <div className="flex max-w-lg flex-col gap-8">
      <h1 className="text-2xl font-bold text-brand-dark">Profilo utente</h1>
      {message && <p className="rounded-md bg-slate-100 px-3 py-2 text-sm">{message}</p>}

      <form onSubmit={handleSaveName} className="flex flex-col gap-3">
        <Field label="Email" value={email} onChange={() => undefined} type="email" disabled />
        <Field label="Nome e cognome" value={fullName} onChange={setFullName} />
        <button
          type="submit"
          className="w-fit rounded-md bg-brand-blue px-4 py-2 font-semibold text-white"
        >
          Salva nome
        </button>
      </form>

      <form onSubmit={handleChangePassword} className="flex flex-col gap-3">
        <Field
          label="Nuova password"
          type="password"
          value={newPassword}
          onChange={setNewPassword}
        />
        <button
          type="submit"
          className="w-fit rounded-md border border-slate-300 px-4 py-2 font-semibold text-slate-700"
        >
          Cambia password
        </button>
      </form>
    </div>
  );
}
