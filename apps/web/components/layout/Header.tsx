"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { PLAN_LABELS } from "@/lib/planLabels";
import { useSubscription } from "@/lib/queries/billing";
import { createClient } from "@/lib/supabase/client";

export function Header({
  email,
  organizationName,
}: {
  email: string | null;
  organizationName: string | null;
}) {
  const router = useRouter();
  const supabase = createClient();
  const subscriptionQuery = useSubscription();
  const subscription = subscriptionQuery.data;

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  const trialDaysLeft =
    subscription?.status === "trialing" && subscription.trial_ends_at
      ? Math.max(
          0,
          Math.ceil(
            (new Date(subscription.trial_ends_at).getTime() - Date.now()) /
              (1000 * 60 * 60 * 24)
          )
        )
      : null;

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 print:hidden">
      <div className="flex items-center gap-3 text-sm font-medium text-slate-700">
        {organizationName ?? "Nessuna organizzazione associata"}
        {subscription && (
          <Link href="/settings/billing" className="flex items-center gap-2">
            <Badge label={`Piano ${PLAN_LABELS[subscription.plan]}`} variant="info" />
            {trialDaysLeft !== null && (
              <span className="text-xs text-brand-amber">
                Prova: {trialDaysLeft === 0 ? "scade oggi" : `scade tra ${trialDaysLeft} giorni`}
              </span>
            )}
            {subscription.status === "past_due" && (
              <Badge label="Pagamento non riuscito" variant="danger" />
            )}
          </Link>
        )}
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-slate-600">{email}</span>
        <button onClick={handleLogout} className="font-medium text-brand-blue hover:underline">
          Esci
        </button>
      </div>
    </header>
  );
}
