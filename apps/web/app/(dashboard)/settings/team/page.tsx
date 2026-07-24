"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/planLabels";
import { useSubscription } from "@/lib/queries/billing";
import {
  useInviteMember,
  useOrganizationMembers,
  useRemoveMember,
} from "@/lib/queries/organization";
import { createClient } from "@/lib/supabase/client";
import { useToast } from "@/lib/toast";

const ROLE_LABELS: Record<string, string> = { admin: "Admin", viewer: "Viewer" };

export default function TeamSettingsPage() {
  const { showToast } = useToast();
  const supabase = createClient();
  const [currentEmail, setCurrentEmail] = useState<string | null>(null);

  const membersQuery = useOrganizationMembers();
  const subscriptionQuery = useSubscription();
  const inviteMutation = useInviteMember();
  const removeMutation = useRemoveMember();

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setCurrentEmail(data.session?.user.email ?? null);
    });
  }, [supabase]);

  const members = membersQuery.data ?? [];
  const myMembership = members.find((m) => m.email === currentEmail);
  const isAdmin = myMembership?.role === "admin";

  const subscription = subscriptionQuery.data;
  const seatsUsed = subscription?.usage.users_count ?? members.length;
  const seatsLimit = subscription?.entitlements.max_users ?? null;
  const atSeatLimit = seatsLimit !== null && seatsUsed >= seatsLimit;

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) {
      showToast("Indica l'email del collaboratore", "error");
      return;
    }
    try {
      await inviteMutation.mutateAsync({ email: inviteEmail.trim(), role: inviteRole });
      showToast(
        `Invito creato per ${inviteEmail}. L'invio dell'email arriverà con la Fase 7 ` +
          "(provider email transazionale): per ora l'invito è salvato e pronto.",
        "success"
      );
      setInviteEmail("");
      setInviteRole("viewer");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'invito", "error");
    }
  }

  async function handleRemove(userId: string, email: string) {
    if (!window.confirm(`Rimuovere ${email} dall'organizzazione?`)) return;
    try {
      await removeMutation.mutateAsync(userId);
      showToast("Membro rimosso.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante la rimozione", "error");
    }
  }

  if (membersQuery.isLoading) {
    return (
      <div className="flex max-w-2xl flex-col gap-4">
        <h1 className="text-2xl font-bold text-brand-dark">Membri del team</h1>
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-dark">Membri del team</h1>
        {subscription && (
          <p className="mt-1 text-sm text-slate-500">
            {seatsUsed}
            {seatsLimit !== null ? ` / ${seatsLimit}` : ""} posti utilizzati sul piano{" "}
            {PLAN_LABELS[subscription.plan]}
            {seatsLimit !== null && (
              <>
                {" · "}
                <Link href="/settings/billing" className="text-brand-blue hover:underline">
                  passa a un piano superiore
                </Link>
              </>
            )}
          </p>
        )}
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Utente</th>
              <th className="px-4 py-2">Ruolo</th>
              <th className="px-4 py-2">Dal</th>
              {isAdmin && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {members.map((member) => (
              <tr key={member.user_id}>
                <td className="px-4 py-2 text-slate-700">
                  {member.full_name ?? member.email}
                  {member.email === currentEmail && (
                    <span className="ml-2 text-xs text-slate-500">(tu)</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <Badge
                    label={ROLE_LABELS[member.role] ?? member.role}
                    variant={member.role === "admin" ? "info" : "neutral"}
                  />
                </td>
                <td className="px-4 py-2 text-slate-500">{formatDate(member.joined_at)}</td>
                {isAdmin && (
                  <td className="px-4 py-2 text-right">
                    {member.email !== currentEmail && (
                      <button
                        onClick={() => handleRemove(member.user_id, member.email)}
                        className="text-xs font-medium text-red-600 hover:underline"
                      >
                        Rimuovi
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isAdmin ? (
        <form
          onSubmit={handleInvite}
          className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-5"
        >
          <p className="font-semibold text-slate-700">Invita un collaboratore</p>
          {atSeatLimit && (
            <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
              Hai raggiunto il numero massimo di posti del piano {PLAN_LABELS[subscription!.plan]}.{" "}
              <Link
                href="/settings/billing"
                className="font-medium text-brand-blue hover:underline"
              >
                Passa a un piano superiore
              </Link>{" "}
              per invitare altri collaboratori.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <input
              type="email"
              aria-label="Email del collaboratore da invitare"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="email@azienda.it"
              required
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
            />
            <select
              aria-label="Ruolo del collaboratore da invitare"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
            >
              {inviteMutation.isPending ? "Invio…" : "Invita"}
            </button>
          </div>
        </form>
      ) : (
        <p className="text-sm text-slate-500">
          Solo un amministratore dell&apos;organizzazione può invitare o rimuovere collaboratori.
        </p>
      )}
    </div>
  );
}
