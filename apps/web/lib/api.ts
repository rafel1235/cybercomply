/** Helper per chiamare l'API FastAPI con il token Supabase corrente. */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Errore tipizzato con lo status HTTP, così i chiamanti possono distinguere ad es. un
 * 404 "risorsa non ancora creata" (stato legittimo) da un vero errore da mostrare. */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch(path: string, accessToken: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(body.detail ?? `Errore API (${response.status})`, response.status);
  }

  // Le risposte 204 (es. DELETE) non hanno corpo: response.json() lancerebbe un errore
  // di parsing su stringa vuota.
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

/** Variante di apiFetch senza token, per gli endpoint pubblici (es. questionario fornitori
 * compilabile senza account): il possesso del link/token è di per sé la credenziale. */
export async function apiFetchPublic(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(body.detail ?? `Errore API (${response.status})`, response.status);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

/** Variante di apiFetch per endpoint binari (es. download PDF), che restituisce un Blob
 * invece di fare il parsing JSON della risposta. */
export async function apiFetchBlob(path: string, accessToken: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(body.detail ?? `Errore API (${response.status})`, response.status);
  }

  return response.blob();
}
