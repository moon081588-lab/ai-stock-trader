import { Link } from "react-router-dom";

import { formatKrwCompact, formatPct, toneClass } from "../lib/format";
import type { SectorPerformance } from "../lib/types";

interface Props {
  sectors: SectorPerformance[];
  loading: boolean;
}

/** Horizontal bar scaled to the largest absolute move on screen. */
function Bar({ value, max }: { value: number; max: number }) {
  const width = max ? Math.min(Math.abs(value) / max, 1) * 100 : 0;
  return (
    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-raised">
      <div
        className="absolute inset-y-0 rounded-full"
        style={{
          width: `${width}%`,
          left: value >= 0 ? "0" : undefined,
          right: value < 0 ? "0" : undefined,
          background: value >= 0 ? "#F5636E" : "#5B8DEF",
        }}
      />
    </div>
  );
}

export default function SectorTable({ sectors, loading }: Props) {
  if (loading && sectors.length === 0) {
    return (
      <div className="flex flex-col gap-2 px-5 pb-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded-xl bg-raised/50" />
        ))}
      </div>
    );
  }

  if (sectors.length === 0) {
    return (
      <p className="px-5 py-12 text-center text-sm text-ink-faint">
        업종 데이터를 준비하는 중이에요
      </p>
    );
  }

  const max = Math.max(...sectors.map((s) => Math.abs(s.change_pct)), 0.01);

  return (
    <div className="flex flex-col">
      <div className="flex flex-col gap-0.5 px-3">
        {sectors.map((sector) => (
          <div
            key={sector.sector}
            className="grid grid-cols-[1fr_auto] items-center gap-4 rounded-xl px-2 py-2.5 transition-colors hover:bg-hover"
          >
            <div className="min-w-0">
              <div className="flex items-baseline gap-2">
                <span className="text-[0.9375rem] font-semibold">{sector.sector}</span>
                <span className="text-2xs text-ink-faint">{sector.count}종목</span>
              </div>
              <div className="mt-1.5 max-w-[280px]">
                <Bar value={sector.change_pct} max={max} />
              </div>
              <div className="mt-1.5 text-2xs text-ink-faint">
                주도{" "}
                <Link
                  to={`/stock/${encodeURIComponent(sector.leader_symbol)}`}
                  className="text-ink-muted hover:underline"
                >
                  {sector.leader_name}
                </Link>{" "}
                <span className={toneClass(sector.leader_change_pct)}>
                  {formatPct(sector.leader_change_pct)}
                </span>
              </div>
            </div>

            <div className="text-right">
              <div className={`num text-lg font-bold ${toneClass(sector.change_pct)}`}>
                {formatPct(sector.change_pct)}
              </div>
              <div className="num text-2xs text-ink-faint">
                {formatKrwCompact(sector.turnover)}
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="px-5 py-4 text-2xs leading-relaxed text-ink-faint">
        추적 중인 24개 종목의 단순 평균이에요. 전체 시장 업종 지수가 아니라서 종목 수가
        적은 업종은 한두 종목에 좌우돼요. 레버리지·인버스 상품은 제외했어요.
      </p>
    </div>
  );
}
