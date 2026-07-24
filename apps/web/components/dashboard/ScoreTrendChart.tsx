import { formatDate } from "@/lib/format";
import type { ComplianceHistoryPoint } from "@/lib/queries/compliance";

const WIDTH = 600;
const HEIGHT = 220;
const PADDING = 32;
const TICKS = [0, 25, 50, 75, 100];

/**
 * Grafico andamento score nel tempo, disegnato a mano in SVG (nessuna libreria come
 * recharts): evita di dipendere da un nuovo pacchetto npm solo per una linea con pochi
 * punti, e resta leggero e facilmente ispezionabile.
 */
export function ScoreTrendChart({ points }: { points: ComplianceHistoryPoint[] }) {
  if (points.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        Ancora nessuno storico da mostrare: aggiorna una misura nel Compliance Tracker per iniziare
        a vedere l&apos;andamento nel tempo.
      </p>
    );
  }

  const innerWidth = WIDTH - PADDING * 2;
  const innerHeight = HEIGHT - PADDING * 2;

  const xForIndex = (i: number) =>
    points.length === 1
      ? PADDING + innerWidth / 2
      : PADDING + (innerWidth * i) / (points.length - 1);
  const yForScore = (score: number) => PADDING + innerHeight * (1 - score / 100);

  const linePoints = points
    .map((p, i) => `${xForIndex(i)},${yForScore(p.score_percent)}`)
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full"
      role="img"
      aria-label="Andamento dell'indice di conformità nel tempo"
    >
      {TICKS.map((tick) => (
        <g key={tick}>
          <line
            x1={PADDING}
            x2={WIDTH - PADDING}
            y1={yForScore(tick)}
            y2={yForScore(tick)}
            stroke="#e2e8f0"
            strokeWidth={1}
          />
          <text x={2} y={yForScore(tick) + 4} fontSize={10} fill="#94a3b8">
            {tick}%
          </text>
        </g>
      ))}
      <polyline points={linePoints} fill="none" stroke="#1B6EC2" strokeWidth={2} />
      {points.map((p, i) => (
        <circle
          key={`${p.recorded_at}-${i}`}
          cx={xForIndex(i)}
          cy={yForScore(p.score_percent)}
          r={3}
          fill="#1B6EC2"
        />
      ))}
      <text x={PADDING} y={HEIGHT - 6} fontSize={10} fill="#94a3b8">
        {formatDate(points[0].recorded_at)}
      </text>
      <text x={WIDTH - PADDING} y={HEIGHT - 6} fontSize={10} fill="#94a3b8" textAnchor="end">
        {formatDate(points[points.length - 1].recorded_at)}
      </text>
    </svg>
  );
}
