/**
 * Dashboard principale — versione stub. Le card complete (indice di conformità, stato
 * NIS2/CRA, grafico andamento, quick actions) arrivano in Fase 4: qui c'è la conferma che
 * l'autenticazione e il layout protetto funzionano end-to-end.
 */
export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold text-brand-dark">Dashboard</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StubCard title="Indice di conformità" value="—" note="Disponibile in Fase 4" />
        <StubCard title="Stato NIS2" value="—" note="Disponibile dopo l'Assessment (Fase 4)" />
        <StubCard title="Stato CRA" value="—" note="Disponibile dopo l'Assessment (Fase 4)" />
        <StubCard title="Prossime scadenze" value="—" note="Disponibile in Fase 4" />
      </div>
    </div>
  );
}

function StubCard({ title, value, note }: { title: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="text-2xl font-bold text-brand-dark">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{note}</p>
    </div>
  );
}
