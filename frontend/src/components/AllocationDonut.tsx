import type { Position } from "../lib/types";

const PALETTE = ["#3182F6", "#F5636E", "#F2A93B", "#26A96C", "#8B5CF6", "#EC4899", "#0EA5E9"];
const REST = "#3A3D47";

/** SVG donut. Positions with no live price are folded into a neutral "미평가" slice. */
export default function AllocationDonut({ positions }: { positions: Position[] }) {
  const priced = positions.filter((p) => p.market_value != null && p.market_value > 0);
  const total = priced.reduce((sum, p) => sum + (p.market_value ?? 0), 0);

  if (total === 0) {
    return (
      <div className="flex h-[180px] items-center justify-center text-sm text-ink-faint">
        평가할 보유 종목이 없어요
      </div>
    );
  }

  const size = 180;
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  const slices = priced.map((p, i) => {
    const fraction = (p.market_value ?? 0) / total;
    const slice = {
      symbol: p.symbol,
      color: i < PALETTE.length ? PALETTE[i] : REST,
      dash: fraction * circumference,
      offset,
      pct: fraction * 100,
    };
    offset += slice.dash;
    return slice;
  });

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {slices.map((s) => (
            <circle
              key={s.symbol}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={s.color}
              strokeWidth="22"
              strokeDasharray={`${s.dash} ${circumference - s.dash}`}
              strokeDashoffset={-s.offset}
            />
          ))}
        </g>
        <text
          x="50%"
          y="47%"
          textAnchor="middle"
          className="fill-ink-faint"
          style={{ fontSize: 12 }}
        >
          종목 수
        </text>
        <text
          x="50%"
          y="60%"
          textAnchor="middle"
          className="fill-ink"
          style={{ fontSize: 24, fontWeight: 700 }}
        >
          {priced.length}
        </text>
      </svg>

      <ul className="flex min-w-0 flex-1 flex-col gap-2">
        {slices.slice(0, 7).map((s) => (
          <li key={s.symbol} className="flex items-center gap-2.5 text-sm">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: s.color }} />
            <span className="min-w-0 flex-1 truncate text-ink-muted">{s.symbol}</span>
            <span className="num font-semibold">{s.pct.toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
