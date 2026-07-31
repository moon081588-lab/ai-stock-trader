import { Link } from "react-router-dom";

import { formatKrwCompact, formatPct, formatPrice, toneClass } from "../lib/format";
import type { MarketFilter, MoverRow, SortKey } from "../lib/types";
import TickerAvatar from "./TickerAvatar";

const MARKETS: { value: MarketFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "KR", label: "국내" },
  { value: "US", label: "해외" },
];

const SORTS: { value: SortKey; label: string }[] = [
  { value: "turnover", label: "거래대금" },
  { value: "volume", label: "거래량" },
  { value: "market_cap", label: "시가총액" },
  { value: "gainers", label: "급상승" },
  { value: "losers", label: "급하락" },
];

interface Props {
  rows: MoverRow[];
  loading: boolean;
  market: MarketFilter;
  sortBy: SortKey;
  onMarketChange: (value: MarketFilter) => void;
  onSortChange: (value: SortKey) => void;
  watched: Set<string>;
  onToggleWatch: (symbol: string) => void;
  asOf: string | null;
}

function Heart({ filled }: { filled: boolean }) {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden>
      <path
        d="M12 20.5 3.8 12.6a5.1 5.1 0 0 1 7.2-7.2l1 1 1-1a5.1 5.1 0 0 1 7.2 7.2z"
        fill={filled ? "#F5636E" : "#3A3D47"}
      />
    </svg>
  );
}

export default function MoversTable({
  rows,
  loading,
  market,
  sortBy,
  onMarketChange,
  onSortChange,
  watched,
  onToggleWatch,
  asOf,
}: Props) {
  return (
    <section className="card overflow-hidden">
      <div className="flex items-center gap-4 px-5 pt-5">
        <h2 className="text-[1.0625rem] font-bold">실시간 차트</h2>
        <span className="text-[0.8125rem] text-ink-faint">
          {asOf ? `${asOf} 기준 · 지연 시세` : "지연 시세"}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 px-4 py-3">
        {MARKETS.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => onMarketChange(m.value)}
            className={`chip ${market === m.value ? "chip-active" : ""}`}
          >
            {m.label}
          </button>
        ))}
        <span className="mx-1.5 h-4 w-px bg-line" />
        {SORTS.map((s) => (
          <button
            key={s.value}
            type="button"
            onClick={() => onSortChange(s.value)}
            className={`chip ${sortBy === s.value ? "chip-active" : ""}`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse">
          <thead>
            <tr className="text-[0.8125rem] text-ink-faint">
              <th className="w-16 py-2 pl-5 text-left font-medium">순위</th>
              <th className="py-2 text-left font-medium">종목</th>
              <th className="py-2 pr-6 text-right font-medium">현재가</th>
              <th className="py-2 pr-6 text-right font-medium">등락률</th>
              <th className="py-2 pr-6 text-right font-medium">거래대금</th>
              <th className="py-2 pr-5 text-right font-medium">시가총액</th>
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0
              ? Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={6} className="px-5 py-2">
                      <div className="h-9 animate-pulse rounded-lg bg-raised/50" />
                    </td>
                  </tr>
                ))
              : rows.map((row) => {
                  const strong = Math.abs(row.change_pct) >= 5;
                  return (
                    <tr key={row.symbol} className="group transition-colors hover:bg-hover">
                      <td className="py-2.5 pl-5">
                        <div className="flex items-center gap-2.5">
                          <button
                            type="button"
                            onClick={() => onToggleWatch(row.symbol)}
                            aria-label={`${row.name} 관심 종목 토글`}
                            className="opacity-70 transition-opacity hover:opacity-100"
                          >
                            <Heart filled={watched.has(row.symbol)} />
                          </button>
                          <span className="num text-sm text-ink-muted">{row.rank}</span>
                        </div>
                      </td>
                      <td className="py-2.5">
                        <Link
                          to={`/stock/${encodeURIComponent(row.symbol)}`}
                          className="flex items-center gap-2.5"
                        >
                          <TickerAvatar symbol={row.symbol} name={row.name} />
                          <div className="min-w-0">
                            <div className="truncate text-[0.9375rem] font-semibold group-hover:underline">
                              {row.name}
                            </div>
                            <div className="text-2xs text-ink-faint">
                              {row.symbol}
                              {row.kind === "etf" && <span className="tag ml-1.5">ETF</span>}
                            </div>
                          </div>
                        </Link>
                      </td>
                      <td className="num py-2.5 pr-6 text-right text-[0.9375rem] font-semibold">
                        {formatPrice(row.price, row.market === "KR" ? 0 : 2, row.market === "KR" ? "원" : "$")}
                      </td>
                      <td className="py-2.5 pr-6 text-right">
                        <span
                          className={`num inline-block rounded-md px-2 py-1 text-[0.9375rem] font-bold ${toneClass(
                            row.change_pct,
                          )} ${
                            strong
                              ? row.change_pct > 0
                                ? "bg-up-soft"
                                : "bg-down-soft"
                              : ""
                          }`}
                        >
                          {formatPct(row.change_pct)}
                        </span>
                      </td>
                      <td className="num py-2.5 pr-6 text-right text-sm text-ink-muted">
                        {formatKrwCompact(row.turnover)}
                      </td>
                      <td className="num py-2.5 pr-5 text-right text-sm text-ink-muted">
                        {formatKrwCompact(row.market_cap)}
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>

      {!loading && rows.length === 0 && (
        <p className="px-5 py-10 text-center text-sm text-ink-faint">
          표시할 종목이 없어요. 잠시 후 다시 시도해 주세요.
        </p>
      )}
    </section>
  );
}
