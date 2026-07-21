"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * Client Supabase lato browser. Usato dai form di login/registrazione/reset password:
 * Supabase gestisce l'intero ciclo di vita delle credenziali, il backend FastAPI si limita
 * a verificare il JWT emesso (vedi apps/api/app/core/security.py).
 */
export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY non configurati. " +
        "Compila apps/web/.env.local con i valori reali del progetto Supabase."
    );
  }

  return createBrowserClient(url, anonKey);
}
