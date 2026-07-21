"use client";

import { useRouter } from "next/navigation";
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

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
      <div className="text-sm font-medium text-slate-700">
        {organizationName ?? "Nessuna organizzazione associata"}
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
