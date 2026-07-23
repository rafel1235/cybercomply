/** Formattazione date coerente in italiano, usata da tutti i moduli della Fase 4. */

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("it-IT", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("it-IT", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatRelativeToNow(iso: string | null | undefined): string {
  if (!iso) return "—";
  const target = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = target - now;
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "oggi";
  if (diffDays > 0) return `tra ${diffDays} giorn${diffDays === 1 ? "o" : "i"}`;
  return `${Math.abs(diffDays)} giorn${Math.abs(diffDays) === 1 ? "o" : "i"} fa`;
}
