import { redirect } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { apiFetch } from "@/lib/api";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const supabase = createServerSupabaseClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  let organizationName: string | null = null;
  try {
    const me = await apiFetch("/auth/me", session.access_token);
    organizationName = me.organizations?.[0]?.name ?? null;
  } catch {
    // Se il backend non è raggiungibile o l'utente non è ancora sincronizzato,
    // la dashboard resta comunque utilizzabile: l'header mostra un fallback.
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header email={session.user.email ?? null} organizationName={organizationName} />
        <main className="flex-1 bg-slate-50 p-6">{children}</main>
      </div>
    </div>
  );
}
