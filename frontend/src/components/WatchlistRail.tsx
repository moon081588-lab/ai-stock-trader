import { Link } from "react-router-dom";

import {
  convert,
  currencyDecimals,
  currencyUnit,
  formatPct,
  formatPrice,
  formatSigned,
  toneClass,
} from "../lib/format";
import type { Currency, WatchlistEntry } from "../lib/types";
import TickerAvatar from "./TickerAvatar";

interface Props {
  entries: WatchlistEntry[];
  loading: boolean;
  onRemove: (symbol: string) => void;
  headline: string | null;
  currency: Currency;
  usdkrw: number | null;
  onCurrencyChange: (value: Currency) => void;
}

export default function WatchlistRail({
  entries,
  loading,
  onRemove,
  headline,
  currency,
  usdkrw,
  onCurrencyChange,
}: Props) {
  return (
    <aside className="flex h-full w-[360px] shrink-0 flex-col gap-4 border-l border-line bg-base px-5 py-5">
      <div className="flex items-center justify-between">
        <h2 className="text-[1.0625rem] font-bold">관심</h2>

        <div className="flex items-center rounded-full bg-raised p-0.5">
          {(["USD", "KRW"] as const).map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => onCurrencyChange(code)}
              disabled={!usdkrw}
              aria-label={code === "USD" ? "달러로 보기" : "원화로 보기"}
              className={`rounded-full px-2.5 py-1 text-2xs font-semibold transition-colors disabled:opacity-40 ${
                currency === code ? "bg-hover text-ink" : "text-ink-faint"
              }`}
            >
              {code === "USD" ? "$" : "원"}
            </button>
          ))}
        </div>
      </div>

      {headline && (
        <div className="card p-4">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-brand">
            <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden>
              <path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z" fill="#3182F6" />
            </svg>
            AI 요약
          </div>
          <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink">{headline}</p>
        </div>
      )}

      <div>
        <h3 className="text-[0.9375rem] font-bold">관심 주식</h3>
        <p className="mt-0.5 text-[0.8125rem] text-ink-faint">
          차트에서 하트를 눌러 추가할 수 있어요
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">
        {loading && entries.length === 0
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-surface" />
            ))
          : entries.map((entry) => (
              <div
                key={entry.symbol}
                className="group flex items-center gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-hover"
              >
                <Link
                  to={`/stock/${encodeURIComponent(entry.symbol)}`}
                  className="flex min-w-0 flex-1 items-center gap-3"
                >
                  <TickerAvatar symbol={entry.symbol} name={entry.name} size={34} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[0.9375rem] font-semibold">{entry.name}</div>
                    <div className="text-2xs text-ink-faint">{entry.symbol}</div>
                  </div>
                </Link>

                <div className="text-right">
                  <div className="num text-[0.9375rem] font-semibold">
                    {entry.price == null
                      ? "—"
                      : formatPrice(
                          convert(entry.price, entry.market, currency, usdkrw),
                          currencyDecimals(currency),
                          currencyUnit(currency),
                        )}
                  </div>
                  {entry.change != null && entry.change_pct != null && (
                    <div className={`num text-2xs font-semibold ${toneClass(entry.change)}`}>
                      {formatSigned(
                        convert(entry.change, entry.market, currency, usdkrw),
                        currencyDecimals(currency),
                      )}{" "}
                      ({formatPct(entry.change_pct)})
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => onRemove(entry.symbol)}
                  aria-label={`${entry.name} 관심 해제`}
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>
                    <path
                      d="M12 20.5 3.8 12.6a5.1 5.1 0 0 1 7.2-7.2l1 1 1-1a5.1 5.1 0 0 1 7.2 7.2z"
                      fill="#F5636E"
                    />
                  </svg>
                </button>
              </div>
            ))}

        {!loading && entries.length === 0 && (
          <p className="py-10 text-center text-sm text-ink-faint">관심 종목이 아직 없어요</p>
        )}
      </div>
    </aside>
  );
}
