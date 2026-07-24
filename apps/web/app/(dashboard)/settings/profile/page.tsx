"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Field } from "@/components/auth/Field";
import { useDeleteMyAccount, useExportMyData } from "@/lib/queries/gdpr";
import { createClient } from "@/lib/supabase/client";

const DELETE_CONFIRMATION_WORD = "ELIMINA";

export default function ProfileSettingsPage() {
  const supabase = createClient();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const exportMyData = useExportMyData();
  const deleteMyAccount = useDeleteMyAccount();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  async function handleDeleteAccount() {
    setDeleteError(null);
    deleteMyAccount.mutate(undefined, {
      onSuccess: async () => {
        await supabase.auth.signOut();
        router.push("/login");
      },
      onError: (error) =>
        setDeleteError(
          error instanceof Error
            ? error.message
            : "Errore durante la cancellazione dell'account."
        ),
    });
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

      <section className="flex flex-col gap-3 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-brand-dark">Privacy e dati</h2>
        <p className="text-sm text-slate-600">
          In base al GDPR (art. 20 — diritto alla portabilità dei dati) puoi scaricare in
          qualsiasi momento una copia di tutti i tuoi dati e di quelli delle organizzazioni
          di cui fai parte, in formato leggibile da macchina (JSON).
        </p>
        <button
          type="button"
          onClick={() => {
            setMessage(null);
            exportMyData.mutate(undefined, {
              onError: (error) =>
                setMessage(
                  error instanceof Error
                    ? error.message
                    : "Errore durante l'esportazione dei dati."
                ),
            });
          }}
          disabled={exportMyData.isPending}
          className="w-fit rounded-md border border-slate-300 px-4 py-2 font-semibold text-slate-700 disabled:opacity-60"
        >
          {exportMyData.isPending ? "Esportazione in corso..." : "Esporta i miei dati"}
        </button>
      </section>

      <section className="flex flex-col gap-3 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-red-700">Zona pericolosa</h2>
        <p className="text-sm text-slate-600">
          In base al GDPR (art. 17 — diritto alla cancellazione) puoi cancellare il tuo
          account in qualsiasi momento. Se sei l&apos;unico membro di un&apos;organizzazione,
          anche tutti i suoi dati (assessment, documenti, incidenti, fornitori) verranno
          cancellati insieme al tuo account. Se ci sono altri membri, verrà rimossa solo
          la tua iscrizione: se sei l&apos;unico amministratore dovrai prima promuoverne un
          altro. L&apos;operazione è immediata e non reversibile.
        </p>

        {!showDeleteConfirm ? (
          <button
            type="button"
            onClick={() => {
              setShowDeleteConfirm(true);
              setDeleteConfirmText("");
              setDeleteError(null);
            }}
            className="w-fit rounded-md border border-red-300 px-4 py-2 font-semibold text-red-700"
          >
            Cancella il mio account
          </button>
        ) : (
          <div className="flex flex-col gap-3 rounded-md border border-red-300 bg-red-50 p-4">
            {deleteError && <p className="text-sm text-red-700">{deleteError}</p>}
            <Field
              label={`Digita "${DELETE_CONFIRMATION_WORD}" per confermare`}
              value={deleteConfirmText}
              onChange={setDeleteConfirmText}
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={
                  deleteConfirmText !== DELETE_CONFIRMATION_WORD || deleteMyAccount.isPending
                }
                className="w-fit rounded-md bg-red-700 px-4 py-2 font-semibold text-white disabled:opacity-50"
              >
                {deleteMyAccount.isPending
                  ? "Cancellazione in corso..."
                  : "Conferma cancellazione definitiva"}
              </button>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="w-fit rounded-md border border-slate-300 px-4 py-2 font-semibold text-slate-700"
              >
                Annulla
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
