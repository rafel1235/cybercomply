/** Skeleton screen generico: la roadmap Fase 4 chiede esplicitamente "skeleton screens,
 * non spinner generici" per i loading state. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-7 w-16" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}
