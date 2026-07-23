"use client";

import { useCallback } from "react";
import { apiFetch, apiFetchBlob } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

/**
 * Hook client-side per chiamare il backend FastAPI con la sessione Supabase corrente.
 * Recupera un token fresco ad ogni chiamata (invece di tenerne uno in stato), così una
 * sessione rinnovata da Supabase in background non causa mai chiamate con token scaduto.
 */
export function useApi() {
  const supabase = createClient();

  const request = useCallback(
    async (path: string, init?: RequestInit) => {
      const { data, error } = await supabase.auth.getSession();
      if (error || !data.session) {
        throw new Error("Sessione scaduta: effettua di nuovo il login.");
      }
      return apiFetch(path, data.session.access_token, init);
    },
    [supabase]
  );

  const get = useCallback((path: string) => request(path), [request]);
  const post = useCallback(
    (path: string, body?: unknown) =>
      request(path, {
        method: "POST",
        body: body !== undefined ? JSON.stringify(body) : undefined,
      }),
    [request]
  );
  const put = useCallback(
    (path: string, body?: unknown) =>
      request(path, {
        method: "PUT",
        body: body !== undefined ? JSON.stringify(body) : undefined,
      }),
    [request]
  );
  const patch = useCallback(
    (path: string, body?: unknown) =>
      request(path, {
        method: "PATCH",
        body: body !== undefined ? JSON.stringify(body) : undefined,
      }),
    [request]
  );
  const del = useCallback((path: string) => request(path, { method: "DELETE" }), [request]);

  const getBlob = useCallback(
    async (path: string) => {
      const { data, error } = await supabase.auth.getSession();
      if (error || !data.session) {
        throw new Error("Sessione scaduta: effettua di nuovo il login.");
      }
      return apiFetchBlob(path, data.session.access_token);
    },
    [supabase]
  );

  return { get, post, put, patch, del, getBlob };
}
