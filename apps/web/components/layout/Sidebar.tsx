"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSubscription } from "@/lib/queries/billing";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/assessment", label: "Assessment" },
  { href: "/dashboard/compliance", label: "Compliance Tracker" },
  { href: "/dashboard/incidents", label: "Incident Reporting", gate: "incident_reporting_enabled" as const },
  { href: "/dashboard/suppliers", label: "Supply Chain", gate: "supply_chain_enabled" as const },
];

const SETTINGS_ITEMS = [
  { href: "/settings/profile", label: "Profilo" },
  { href: "/settings/organization", label: "Organizzazione" },
  { href: "/settings/team", label: "Team" },
  { href: "/settings/billing", label: "Fatturazione" },
];

export function Sidebar() {
  const pathname = usePathname();
  // Usato solo per mostrare un'icona di "modulo non incluso nel piano" accanto alla voce
  // di navigazione: il link resta sempre cliccabile, il blocco vero avviene lato backend
  // (dependency sul router) e la pagina di destinazione mostra l'upsell completo.
  const subscriptionQuery = useSubscription();
  const entitlements = subscriptionQuery.data?.entitlements;

  return (
    <nav className="flex w-60 flex-col gap-6 border-r border-slate-200 bg-white p-4 print:hidden">
      <div className="text-lg font-bold text-brand-dark">
        CyberComply<span className="text-brand-amber">IT</span>
      </div>
      <div className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const locked = item.gate && entitlements ? !entitlements[item.gate] : false;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium ${
                pathname === item.href
                  ? "bg-brand-blue/10 text-brand-blue"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <span>{item.label}</span>
              {locked && (
                <span className="rounded-full bg-brand-amber/15 px-2 py-0.5 text-[10px] font-semibold text-brand-amber">
                  UPGRADE
                </span>
              )}
            </Link>
          );
        })}
      </div>
      <div className="mt-auto flex flex-col gap-1 border-t border-slate-200 pt-4">
        {SETTINGS_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              pathname === item.href
                ? "bg-brand-blue/10 text-brand-blue"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
