"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type ToastType = "success" | "error" | "info";
type ToastItem = { id: number; message: string; type: ToastType };

type ToastContextValue = {
  showToast: (message: string, type?: ToastType) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_STYLES: Record<ToastType, string> = {
  success: "bg-green-600 text-white",
  error: "bg-red-600 text-white",
  info: "bg-brand-dark text-white",
};

/**
 * Sistema di notifiche globale (toast), senza librerie esterne: la roadmap Fase 4 chiede
 * "gestione errori globale (toast notifications per successo/errore)". Ogni pagina chiama
 * `useToast().showToast(...)` nei propri handler di successo/errore.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Fase 10 (accessibilità — WCAG 4.1.3 "Status Messages"): senza role/aria-live, un
          utente di screen reader non viene mai informato che un'azione è riuscita o
          fallita, perché il toast compare e scompare senza mai ricevere il focus.
          `role="alert"` (implica aria-live="assertive") per gli errori, da annunciare
          subito; `role="status"` (aria-live="polite") per successo/info, meno urgente. */}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.type === "error" ? "alert" : "status"}
            className={`pointer-events-auto rounded-md px-4 py-3 text-sm font-medium shadow-lg ${TOAST_STYLES[t.type]}`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast deve essere usato dentro <ToastProvider>");
  }
  return ctx;
}
