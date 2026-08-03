import { memo } from "react";
import { Link } from "react-router-dom";

import {
  convert,
  currencyDecimals,
  currencyUnit,
  formatKrwCompact,
  formatPct,
  formatPrice,
  toneClass,
} from "../lib/format";
import type { Currency, MarketFilter, MoverRow, SortKey } from "../lib/types";
import type { FlashDirection } from "../lib/useLivePrices";
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
  flash: Record<string, FlashDirection>;
  currency: Currency;
  usdkrw: number | null;
  hideLeveraged: boolean;
  onHideLeveragedChange: (value: boolean) => void;
  selected: string | null;
  onSelect: (symbol: string) => void;
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

const Row = memo(function Row({
  row,
  watched,
  flashDir,
  onToggleWatch,
  currency,
  usdkrw,
  selected,
  onSelect,
}: {
  row: MoverRow;
  watched: boolean;
  flashDir: FlashDirection | undefined;
  onToggleWatch: (symbol: string) => void;
  currency: Currency;
  usdkrw: number | null;
  selected: boolean;
  onSelect: (symbol: string) => void;
}) {
  const strong = Math.abs(row.change_pct) >= 5;
  const flashClass =
    flashDir === "up" ? "animate-flashUp" : flashDir === "down" ? "animate-flashDown" : "";

  const price = convert(row.price, row.market, currency, usdkrw);

  return (
    <tr
      onClick={() => onSelect(row.symbol)}
      className={`group cursor-pointer transition-colors ${
        selected ? "bg-hover" : "hover:bg-hover"
      }`}
    >
      <td className="py-2.5 pl-5">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onToggleWatch(row.symbol);
            }}
            aria-label={`${row.name} 관심 종목 토글`}
            className="opacity-70 transition-opacity hover:opacity-100"
          >
            <Heart filled={watched} />
          </button>
          <span className="num text-sm text-ink-muted">{row.rank}</span>
        </div>
      </td>

      <td className="py-2.5">
        <div className="flex items-center gap-2.5">
          <TickerAvatar symbol={row.symbol} name={row.name} />
          <div className="min-w-0">
            <Link
              to={`/stock/${encodeURIComponent(row.symbol)}`}
              onClick={(event) => event.stopPropagation()}
              className="block truncate text-[0.9375rem] font-semibold hover:underline"
            >
              {row.name}
            </Link>
            <div className="flex items-center gap-1.5 text-2xs text-ink-faint">
              {row.symbol}
              {row.kind === "etf" && <span className="tag">ETF</span>}
              {row.leveraged && <span className="tag text-up">레버리지</span>}
            </div>
          </div>
        </div>
      </td>

      {/* whitespace-nowrap everywhere below: Korean figures like 1,147.8조원 were
          breaking across two lines once the preview panel narrowed the table. */}
      <td className="whitespace-nowrap py-2.5 pr-6 text-right">
        <span
          className={`num inline-block rounded-md px-1.5 py-0.5 text-[0.9375rem] font-semibold ${flashClass}`}
        >
          {formatPrice(price, currencyDecimals(currency), currencyUnit(currency))}
        </span>
      </td>

      <td className="whitespace-nowrap py-2.5 pr-6 text-right">
        <span
          className={`num inline-block rounded-md px-2 py-1 text-[0.9375rem] font-bold ${toneClass(
            row.change_pct,
          )} ${strong ? (row.change_pct > 0 ? "bg-up-soft" : "bg-down-soft") : ""}`}
        >
          {formatPct(row.change_pct)}
        </span>
      </td>

      <td className="num whitespace-nowrap py-2.5 pr-6 text-right text-sm text-ink-muted">
        {formatKrwCompact(row.turnover)}
      </td>
      <td className="num hidden whitespace-nowrap py-2.5 pr-5 text-right text-sm text-ink-muted 2xl:table-cell">
        {formatKrwCompact(row.market_cap)}
      </td>
    </tr>
  );
});

export default function MoversTable({
  rows,
  loading,
  market,
  sortBy,
  onMarketChange,
  onSortChange,
  watched,
  onToggleWatch,
  flash,
  currency,
  usdkrw,
  hideLeveraged,
  onHideLeveragedChange,
  selected,
  onSelect,
}: Props) {
  return (
    <div className="flex min-w-0 flex-1 flex-col">
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
        <span className="mx-1.5 h-4 w-px bg-line" />
        <button
          type="button"
          onClick={() => onHideLeveragedChange(!hideLeveraged)}
          className={`chip flex items-center gap-1.5 whitespace-nowrap ${
            hideLeveraged ? "chip-active" : ""
          }`}
        >
          <span
            className={`grid h-4 w-4 shrink-0 place-items-center rounded-full transition-colors ${
              hideLeveraged ? "bg-brand" : "border border-line"
            }`}
          >
            {hideLeveraged && (
              <svg width="9" height="9" viewBox="0 0 12 12" aria-hidden>
                <path
                  d="M2.5 6.2 4.8 8.5 9.5 3.8"
                  fill="none"
                  stroke="#fff"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </span>
          투자위험 종목 숨기기
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            <tr className="text-[0.8125rem] text-ink-faint">
              <th className="w-16 py-2 pl-5 text-left font-medium">순위</th>
              <th className="py-2 text-left font-medium">종목</th>
              <th className="py-2 pr-6 text-right font-medium">현재가</th>
              <th className="py-2 pr-6 text-right font-medium">등락률</th>
              <th className="whitespace-nowrap py-2 pr-6 text-right font-medium">거래대금</th>
              <th className="hidden whitespace-nowrap py-2 pr-5 text-right font-medium 2xl:table-cell">
                시가총액
              </th>
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
              : rows.map((row) => (
                  <Row
                    key={row.symbol}
                    row={row}
                    watched={watched.has(row.symbol)}
                    flashDir={flash[row.symbol]}
                    onToggleWatch={onToggleWatch}
                    currency={currency}
                    usdkrw={usdkrw}
                    selected={selected === row.symbol}
                    onSelect={onSelect}
                  />
                ))}
          </tbody>
        </table>
      </div>

      {!loading && rows.length === 0 && (
        <p className="px-5 py-10 text-center text-sm text-ink-faint">
          표시할 종목이 없어요. 잠시 후 다시 시도해 주세요.
        </p>
      )}
    </div>
  );
}
