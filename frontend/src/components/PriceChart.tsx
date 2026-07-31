import { useMemo, useState } from "react";

import type { Bar, Forecast } from "../lib/types";

const UP = "#F5636E";
const DOWN = "#5B8DEF";
const GRID = "#23252E";
const AXIS = "#6B7180";
const BAND = "#8B8FF5";

const WIDTH = 900;
const HEIGHT = 380;
const PAD = { top: 16, right: 68, bottom: 26, left: 12 };

interface Props {
  bars: Bar[];
  forecast: Forecast | null;
  /** Trading days of projection to draw. 0 hides the cone entirely. */
  horizonDays: number;
  currency: string;
}

interface Hover {
  x: number;
  bar: Bar;
}

function niceTicks(min: number, max: number, count = 5): number[] {
  const raw = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? mag * 10;
  const start = Math.ceil(min / step) * step;

  const ticks: number[] = [];
  for (let v = start; v <= max; v += step) ticks.push(v);
  return ticks;
}

export default function PriceChart({ bars, forecast, horizonDays, currency }: Props) {
  const [hover, setHover] = useState<Hover | null>(null);

  const model = useMemo(() => {
    if (bars.length < 2) return null;

    // Forecast points are appended to the right of history on the same x scale,
    // so the cone reads as a continuation rather than a separate chart.
    const cone =
      forecast && horizonDays > 0
        ? forecast.points.filter((p) => p.horizon_days <= horizonDays)
        : [];
    const futureSpan = cone.length ? Math.max(...cone.map((p) => p.horizon_days)) : 0;
    const totalSlots = bars.length + futureSpan;

    const lows = bars.map((b) => b.low);
    const highs = bars.map((b) => b.high);
    const min = Math.min(...lows, ...cone.map((p) => p.low));
    const max = Math.max(...highs, ...cone.map((p) => p.high));
    const padding = (max - min) * 0.06 || 1;

    const plotW = WIDTH - PAD.left - PAD.right;
    const plotH = HEIGHT - PAD.top - PAD.bottom;
    const lo = min - padding;
    const hi = max + padding;

    const x = (slot: number) => PAD.left + (slot / Math.max(totalSlots - 1, 1)) * plotW;
    const y = (price: number) => PAD.top + (1 - (price - lo) / (hi - lo)) * plotH;

    return { cone, x, y, lo, hi, plotW, plotH, candleW: Math.max(1.2, plotW / totalSlots - 1) };
  }, [bars, forecast, horizonDays]);

  if (!model) {
    return (
      <div className="grid h-[380px] place-items-center text-sm text-ink-faint">
        차트를 그릴 데이터가 부족해요
      </div>
    );
  }

  const { cone, x, y, lo, hi, candleW } = model;
  const last = bars[bars.length - 1];
  const lastX = x(bars.length - 1);

  const upper = cone.map((p) => `${x(bars.length - 1 + p.horizon_days)},${y(p.high)}`);
  const lower = cone.map((p) => `${x(bars.length - 1 + p.horizon_days)},${y(p.low)}`).reverse();
  const conePolygon = cone.length
    ? `${lastX},${y(last.close)} ${upper.join(" ")} ${lower.join(" ")}`
    : "";
  const medianPath = cone.length
    ? `M${lastX},${y(last.close)} ` +
      cone
        .map((p) => `L${x(bars.length - 1 + p.horizon_days)},${y(p.expected_price)}`)
        .join(" ")
    : "";

  const onMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * WIDTH;
    const slot = Math.round(
      ((px - PAD.left) / (WIDTH - PAD.left - PAD.right)) *
        (bars.length + (cone.length ? Math.max(...cone.map((p) => p.horizon_days)) : 0) - 1),
    );
    if (slot < 0 || slot > bars.length - 1) return setHover(null);
    setHover({ x: x(slot), bar: bars[slot] });
  };

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="가격 캔들 차트와 예측 구간"
      >
        {niceTicks(lo, hi).map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke={GRID}
              strokeWidth="1"
            />
            <text
              x={WIDTH - PAD.right + 8}
              y={y(tick) + 4}
              fill={AXIS}
              fontSize="11"
              className="num"
            >
              {tick.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}
            </text>
          </g>
        ))}

        {cone.length > 0 && (
          <>
            <polygon points={conePolygon} fill={BAND} fillOpacity="0.14" />
            <path d={medianPath} stroke={BAND} strokeWidth="1.6" strokeDasharray="5 4" fill="none" />
            <line
              x1={lastX}
              x2={lastX}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke={AXIS}
              strokeWidth="1"
              strokeDasharray="3 3"
            />
          </>
        )}

        {bars.map((bar, i) => {
          const rising = bar.close >= bar.open;
          const color = rising ? UP : DOWN;
          const cx = x(i);
          const top = y(Math.max(bar.open, bar.close));
          const bottom = y(Math.min(bar.open, bar.close));
          return (
            <g key={bar.date}>
              <line x1={cx} x2={cx} y1={y(bar.high)} y2={y(bar.low)} stroke={color} strokeWidth="1" />
              <rect
                x={cx - candleW / 2}
                y={top}
                width={candleW}
                height={Math.max(bottom - top, 1)}
                fill={color}
              />
            </g>
          );
        })}

        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={y(last.close)}
          y2={y(last.close)}
          stroke={AXIS}
          strokeWidth="1"
          strokeDasharray="2 4"
        />

        {hover && (
          <line
            x1={hover.x}
            x2={hover.x}
            y1={PAD.top}
            y2={HEIGHT - PAD.bottom}
            stroke="#5A5F6B"
            strokeWidth="1"
          />
        )}
      </svg>

      {hover && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-raised px-3 py-2 text-2xs">
          <div className="text-ink-faint">{hover.bar.date}</div>
          <div className="num mt-1 flex gap-3">
            <span>시 {hover.bar.open.toLocaleString("ko-KR")}</span>
            <span>고 {hover.bar.high.toLocaleString("ko-KR")}</span>
            <span>저 {hover.bar.low.toLocaleString("ko-KR")}</span>
            <span className="font-semibold">
              종 {hover.bar.close.toLocaleString("ko-KR")}
              {currency}
            </span>
          </div>
        </div>
      )}

      {cone.length > 0 && (
        <div className="mt-2 flex items-center gap-4 px-1 text-2xs text-ink-faint">
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-4" style={{ background: BAND }} />
            예측 중앙값
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-4 rounded-sm" style={{ background: BAND, opacity: 0.22 }} />
            5~95% 구간
          </span>
          <span>과거 데이터 기반 통계적 추정이며, 투자 조언이 아닙니다</span>
        </div>
      )}
    </div>
  );
}
