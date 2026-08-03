import { Link } from "react-router-dom";

import { api } from "../lib/api";
import {
  convert,
  currencyDecimals,
  currencyUnit,
  formatPct,
  formatPrice,
  formatSigned,
  toneClass,
  toneStroke,
} from "../lib/format";
import type { Currency, MoverRow } from "../lib/types";
import { usePolling } from "../lib/useFetch";
import Sparkline from "./Sparkline";
import TickerAvatar from "./TickerAvatar";

interface Props {
  row: MoverRow | null;
  currency: Currency;
  usdkrw: number | null;
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg bg-raised px-3 py-2">
      <div className="text-2xs text-ink-faint">{label}</div>
      <div className={`num mt-0.5 text-sm font-semibold ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

/**
 * Compact detail beside the table — click a row, see the chart without leaving
 * the board. Deliberately lighter than the full 종목 상세 page: 3 months of
 * closes rather than candles, and no forecast cone.
 */
export default function PreviewPanel({ row, currency, usdkrw }: Props) {
  const symbol = row?.symbol ?? "";
  const detail = usePolling(
    () => (symbol ? api.stock(symbol, "monte_carlo", 90) : Promise.resolve(null)),
    120_000,
    [symbol],
  );

  if (!row) {
    return (
      <div className="grid h-full min-h-[320px] place-items-center px-6 text-center">
        <p className="text-sm leading-relaxed text-ink-faint">
          종목을 선택하면
          <br />
          차트와 지표를 여기서 볼 수 있어요
        </p>
      </div>
    );
  }

  const d = detail.data;
  const unit = currencyUnit(currency);
  const decimals = currencyDecimals(currency);
  const price = convert(row.price, row.market, currency, usdkrw);
  const change = convert(row.change, row.market, currency, usdkrw);
  const closes = (d?.bars ?? []).map((bar) => bar.close);

  return (
    <div className="flex h-full flex-col gap-4 px-5 py-4">
      <div className="flex items-center gap-2.5">
        <TickerAvatar symbol={row.symbol} name={row.name} size={34} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[0.9375rem] font-semibold">{row.name}</div>
          <div className="text-2xs text-ink-faint">
            {row.symbol} · {row.sector}
          </div>
        </div>
      </div>

      <div>
        <div className="num text-xl font-bold">{formatPrice(price, decimals, unit)}</div>
        <div className={`num text-[0.8125rem] font-semibold ${toneClass(row.change)}`}>
          {formatSigned(change, decimals)} ({formatPct(row.change_pct)})
        </div>
      </div>

      <div className="rounded-xl bg-raised/50 px-2 py-3">
        {closes.length > 1 ? (
          <Sparkline
            values={closes}
            stroke={toneStroke(row.change)}
            width={320}
            height={90}
            baseline={false}
          />
        ) : (
          <div className="h-[90px] animate-pulse rounded bg-raised/60" />
        )}
        <div className="mt-1 px-1 text-2xs text-ink-faint">최근 3개월 종가</div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat
          label="연 변동성"
          value={d ? `${d.metrics.annualized_volatility_pct.toFixed(1)}%` : "—"}
        />
        <Stat
          label="최대 낙폭"
          value={d ? `${d.metrics.max_drawdown_pct.toFixed(1)}%` : "—"}
          tone="text-down"
        />
        <Stat label="샤프 지수" value={d ? d.metrics.sharpe_ratio.toFixed(2) : "—"} />
        <Stat
          label="1년 기대수익"
          value={d ? formatPct(d.forecast.expected_return_pct) : "—"}
          tone={d ? toneClass(d.forecast.expected_return_pct) : undefined}
        />
      </div>

      <Link
        to={`/stock/${encodeURIComponent(row.symbol)}`}
        className="mt-auto rounded-xl bg-raised py-2.5 text-center text-sm font-semibold transition-colors hover:bg-hover"
      >
        종목 상세 보기
      </Link>
    </div>
  );
}
