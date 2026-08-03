import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import NewsFeed from "../components/NewsFeed";
import PriceChart from "../components/PriceChart";
import TickerAvatar from "../components/TickerAvatar";
import { api } from "../lib/api";
import { formatPct, formatPrice, formatSigned, toneClass } from "../lib/format";
import type { ForecastMethod } from "../lib/types";
import { usePolling } from "../lib/useFetch";

const RANGES = [
  { label: "3개월", days: 90 },
  { label: "6개월", days: 180 },
  { label: "1년", days: 365 },
  { label: "2년", days: 730 },
];

const METHODS: { value: ForecastMethod; label: string }[] = [
  { value: "monte_carlo", label: "몬테카를로" },
  { value: "drift", label: "드리프트" },
  { value: "linear_trend", label: "선형추세" },
];

const HORIZONS = [
  { label: "예측 없음", days: 0 },
  { label: "1개월", days: 21 },
  { label: "3개월", days: 63 },
  { label: "1년", days: 252 },
];

function Metric({ label, value, tone, hint }: { label: string; value: string; tone?: string; hint?: string }) {
  return (
    <div className="rounded-xl bg-raised px-4 py-3">
      <div className="text-2xs text-ink-faint">{label}</div>
      <div className={`num mt-1 text-lg font-bold ${tone ?? ""}`}>{value}</div>
      {hint && <div className="mt-0.5 text-2xs text-ink-faint">{hint}</div>}
    </div>
  );
}

export default function StockDetail({ onView }: { onView: (symbol: string) => void }) {
  const { symbol = "" } = useParams();

  const onViewRef = useRef(onView);
  onViewRef.current = onView;
  useEffect(() => {
    if (symbol) onViewRef.current(symbol);
  }, [symbol]);
  const [lookback, setLookback] = useState(365);
  const [method, setMethod] = useState<ForecastMethod>("monte_carlo");
  const [horizon, setHorizon] = useState(63);

  const detail = usePolling(
    () => api.stock(symbol, method, lookback),
    120_000,
    [symbol, method, lookback],
  );
  const news = usePolling(() => api.news(symbol), 300_000, [symbol]);

  const d = detail.data;
  const currency = d?.market === "KR" ? "원" : "$";
  const decimals = d?.market === "KR" ? 0 : 2;

  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 pb-10">
      <Link to="/" className="w-fit text-[0.8125rem] text-ink-faint hover:text-ink-muted">
        ← 홈으로
      </Link>

      {detail.error && (
        <div className="rounded-xl bg-up-soft px-4 py-3 text-sm text-up">
          종목 정보를 불러오지 못했어요: {detail.error}
        </div>
      )}

      <section className="card p-6">
        <div className="flex items-center gap-3">
          <TickerAvatar symbol={symbol} name={d?.name ?? symbol} size={44} />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">{d?.name ?? symbol}</h1>
              {d?.kind === "etf" && <span className="tag">ETF</span>}
            </div>
            <div className="text-[0.8125rem] text-ink-faint">{symbol}</div>
          </div>
        </div>

        <div className="mt-4 flex items-baseline gap-3">
          <span className="num text-[2rem] font-bold leading-none">
            {d ? formatPrice(d.price, decimals, currency) : "—"}
          </span>
          {d && (
            <span className={`num text-[0.9375rem] font-semibold ${toneClass(d.change)}`}>
              {formatSigned(d.change, decimals)} ({formatPct(d.change_pct)})
            </span>
          )}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-1.5">
          {RANGES.map((r) => (
            <button
              key={r.days}
              type="button"
              onClick={() => setLookback(r.days)}
              className={`chip ${lookback === r.days ? "chip-active" : ""}`}
            >
              {r.label}
            </button>
          ))}
          <span className="mx-1.5 h-4 w-px bg-line" />
          {HORIZONS.map((h) => (
            <button
              key={h.days}
              type="button"
              onClick={() => setHorizon(h.days)}
              className={`chip ${horizon === h.days ? "chip-active" : ""}`}
            >
              {h.label}
            </button>
          ))}
          <span className="mx-1.5 h-4 w-px bg-line" />
          {METHODS.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => setMethod(m.value)}
              className={`chip ${method === m.value ? "chip-active" : ""}`}
            >
              {m.label}
            </button>
          ))}
        </div>

        <div className="mt-4">
          {detail.loading && !d ? (
            <div className="h-[380px] animate-pulse rounded-xl bg-raised/40" />
          ) : (
            <PriceChart
              bars={d?.bars ?? []}
              forecast={d?.forecast ?? null}
              horizonDays={horizon}
              currency={currency}
            />
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_400px]">
        <div className="flex flex-col gap-4">
          <section className="card p-5">
            <h2 className="pb-4 text-[1.0625rem] font-bold">위험 지표</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <Metric
                label="연평균 성장률"
                value={d ? `${d.metrics.cagr_pct.toFixed(1)}%` : "—"}
                tone={d ? toneClass(d.metrics.cagr_pct) : undefined}
              />
              <Metric
                label="샤프 지수"
                value={d ? d.metrics.sharpe_ratio.toFixed(2) : "—"}
                hint="위험 대비 초과수익"
              />
              <Metric
                label="최대 낙폭"
                value={d ? `${d.metrics.max_drawdown_pct.toFixed(1)}%` : "—"}
                tone="text-down"
              />
              <Metric
                label="연 변동성"
                value={d ? `${d.metrics.annualized_volatility_pct.toFixed(1)}%` : "—"}
              />
              <Metric
                label="1일 VaR (95%)"
                value={d ? `${d.metrics.value_at_risk_95_pct.toFixed(2)}%` : "—"}
                tone="text-down"
                hint="20일 중 1일은 이보다 나쁨"
              />
              <Metric
                label="1년 기대수익"
                value={d ? formatPct(d.forecast.expected_return_pct) : "—"}
                tone={d ? toneClass(d.forecast.expected_return_pct) : undefined}
              />
            </div>
          </section>

          <section className="card overflow-hidden">
            <h2 className="px-5 pb-3 pt-5 text-[1.0625rem] font-bold">기간별 예측</h2>
            <table className="w-full border-collapse">
              <thead>
                <tr className="text-[0.8125rem] text-ink-faint">
                  <th className="py-2 pl-5 text-left font-medium">기간</th>
                  <th className="py-2 pr-6 text-right font-medium">중앙값</th>
                  <th className="py-2 pr-6 text-right font-medium">5~95% 구간</th>
                  <th className="py-2 pr-5 text-right font-medium">신뢰도</th>
                </tr>
              </thead>
              <tbody>
                {(d?.forecast.points ?? []).map((point) => (
                  <tr key={point.horizon_days} className="transition-colors hover:bg-hover">
                    <td className="py-2.5 pl-5 text-sm">{point.horizon_days}일</td>
                    <td className="num py-2.5 pr-6 text-right text-[0.9375rem] font-semibold">
                      {formatPrice(point.expected_price, decimals, currency)}
                    </td>
                    <td className="num py-2.5 pr-6 text-right text-sm text-ink-muted">
                      {formatPrice(point.low, decimals, "")} ~{" "}
                      {formatPrice(point.high, decimals, "")}
                    </td>
                    <td className="py-2.5 pr-5 text-right">
                      <span className="num text-sm text-ink-muted">
                        {(point.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {d && (
              <p className="px-5 py-4 text-2xs leading-relaxed text-ink-faint">
                {d.forecast.disclaimer}
              </p>
            )}
          </section>
        </div>

        <section className="card p-5">
          <h2 className="pb-3 text-[1.0625rem] font-bold">뉴스</h2>
          <NewsFeed news={news.data} loading={news.loading} />
        </section>
      </div>
    </main>
  );
}
