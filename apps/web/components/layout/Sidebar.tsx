"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/assessment", label: "Assessment" },
  { href: "/dashboard/compliance", label: "Compliance Tracker" },
  { href: "/dashboard/incidents", label: "Incident Reporting" },
  { href: "/dashboard/suppliers", label: "Supply Chain" },
];

const SETTINGS_ITEMS = [
  { href: "/settings/profile", label: "Profilo" },
  { href: "/settings/organization", label: "Organizzazione" },
  { href: "/settings/team", label: "Team" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex w-60 flex-col gap-6 border-r border-slate-200 bg-white p-4 print:hidden">
      <div className="text-lg font-bold text-brand-dark">
        CyberComply<span className="text-brand-amber">IT</span>
      </div>
      <div className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => (
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
