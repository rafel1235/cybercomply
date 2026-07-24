"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  PLAN_FEATURES,
  PLAN_LABELS,
  PLAN_ORDER,
  PLAN_PRICE_LABELS,
  PLAN_PURCHASABLE,
  PLAN_TAGLINES,
  SUBSCRIPTION_STATUS_LABELS,
  SUBSCRIPTION_STATUS_VARIANTS,
} from "@/lib/planLabels";
import { useCheckout, usePortal, useSubscription, type Plan } from "@/lib/queries/billing";
import { useToast } from "@/lib/toast";

function formatQuota(used: number, limit: number | null): string {
  if (limit === null) return `${used} generati (illimitati)`;
  return `${used} / ${limit} generati questo mese`;
}

export default function BillingSettingsPage() {
  const { showToast } = useToast();
  const subscriptionQuery = useSubscription();
  const checkoutMutation = useCheckout();
  const portalMutation = usePortal();
  const [pendingPlan, setPendingPlan] = useState<Plan | null>(null);

  // Legge l'esito del redirect da Stripe Checkout solo lato client dopo il mount, come
  // già fatto per ?tab= in compliance/page.tsx: evita di dover avvolgere la pagina in un
  // Suspense boundary solo per un parametro non essenziale al primo render.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const outcome = params.get("checkout");
    if (outcome === "success") {
      showToast("Abbonamento attivato: il piano si aggiornerà a breve.", "success");
    } else if (outcome === "cancelled") {
      showToast("Checkout annullato: nessun addebito effettuato.", "info");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpgrade(plan: Plan) {
    setPendingPlan(plan);
    try {
      const { checkout_url } = await checkoutMutation.mutateAsync(plan);
      window.location.href = checkout_url;
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Errore durante l'avvio del checkout", "error");
      setPendingPlan(null);
    }
  }

  async function handlePortal() {
    try {
      const { portal_url } = await portalMutation.mutateAsync();
      window.location.href = portal_url;
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : "Errore nell'apertura del portale abbonamento",
        "error"
      );
    }
  }

  if (subscriptionQuery.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold text-brand-dark">Fatturazione</h1>
        <CardSkeleton />
      </div>
    );
  }

  if (subscriptionQuery.isError) {
    const message =
      subscriptionQuery.error instanceof ApiError
        ? subscriptionQuery.error.message
        : "Impossibile leggere lo stato dell'abbonamento.";
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold text-brand-dark">Fatturazione</h1>
        <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{message}</p>
      </div>
    );
  }

  const subscription = subscriptionQuery.data!;
  const { entitlements, usage } = subscription;
  const canManageSubscription = subscription.plan !== "free" && subscription.status !== "trialing";

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-bold text-brand-dark">Fatturazione</h1>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-slate-500">Piano attuale</p>
            <p className="text-xl font-bold text-brand-dark">{PLAN_LABELS[subscription.plan]}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              label={SUBSCRIPTION_STATUS_LABELS[subscription.status]}
              variant={SUBSCRIPTION_STATUS_VARIANTS[subscription.status]}
            />
            {canManageSubscription && (
              <button
                onClick={handlePortal}
                disabled={portalMutation.isPending}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                {portalMutation.isPending ? "Apertura…" : "Gestisci abbonamento"}
              </button>
            )}
          </div>
        </div>

        {subscription.status === "trialing" && subscription.trial_ends_at && (
          <p className="mt-3 text-sm text-brand-amber">
            Prova gratuita di Essential attiva, senza carta di credito: scade il{" "}
            {formatDate(subscription.trial_ends_at)}. Passa a un piano a pagamento qui sotto in
            qualsiasi momento, oppure lascia scadere la prova per tornare automaticamente al
            piano Free (i tuoi dati non vengono mai cancellati).
          </p>
        )}
        {subscription.status === "past_due" && (
          <p className="mt-3 text-sm text-red-700">
            L&apos;ultimo pagamento non è andato a buon fine. Aggiorna il metodo di pagamento dal
            portale abbonamento per evitare interruzioni del servizio.
          </p>
        )}
        {subscription.renews_at && subscription.status === "active" && (
          <p className="mt-3 text-xs text-slate-500">
            Prossimo rinnovo: {formatDate(subscription.renews_at)}
          </p>
        )}

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium uppercase text-slate-400">Documenti AI</p>
            <p className="text-sm text-slate-700">
              {formatQuota(usage.documents_generated_this_month, entitlements.max_ai_documents_per_month)}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase text-slate-400">Utenti</p>
            <p className="text-sm text-slate-700">
              {usage.users_count}
              {entitlements.max_users !== null ? ` / ${entitlements.max_users}` : " (illimitati)"}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {PLAN_ORDER.map((plan) => {
          const isCurrent = plan === subscription.plan;
          const purchasable = PLAN_PURCHASABLE[plan];
          return (
            <div
              key={plan}
              className={`flex flex-col gap-3 rounded-lg border bg-white p-5 ${
                isCurrent ? "border-brand-blue ring-1 ring-brand-blue" : "border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="text-lg font-bold text-brand-dark">{PLAN_LABELS[plan]}</p>
                {isCurrent && <Badge label="Piano attuale" variant="info" />}
              </div>
              <p className="text-2xl font-bold text-brand-dark">{PLAN_PRICE_LABELS[plan]}</p>
              <p className="text-sm text-slate-500">{PLAN_TAGLINES[plan]}</p>
              <ul className="flex flex-col gap-1.5 text-sm text-slate-600">
                {PLAN_FEATURES[plan].map((feature) => (
                  <li key={feature} className="flex gap-2">
                    <span className="text-brand-blue">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>
              {!isCurrent && purchasable && (
                <button
                  onClick={() => handleUpgrade(plan)}
                  disabled={checkoutMutation.isPending}
                  className="mt-auto rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
                >
                  {checkoutMutation.isPending && pendingPlan === plan
                    ? "Reindirizzamento…"
                    : `Passa a ${PLAN_LABELS[plan]}`}
                </button>
              )}
              {!isCurrent && !purchasable && plan === "enterprise" && (
                <a
                  href="mailto:info@cybercomplyit.it?subject=Richiesta%20piano%20Enterprise"
                  className="mt-auto rounded-md border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Contattaci
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
