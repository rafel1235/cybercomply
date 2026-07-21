import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/** Client Supabase lato server (Server Components / middleware), basato sui cookie di sessione. */
export function createServerSupabaseClient() {
  const cookieStore = cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

  return createServerClient(url, anonKey, {
    cookies: {
      get(name: string) {
        return cookieStore.get(name)?.value;
      },
      set() {
        // Nei Server Components non possiamo scrivere cookie: gestito dal middleware.
      },
      remove() {
        // idem
      },
    },
  });
}
