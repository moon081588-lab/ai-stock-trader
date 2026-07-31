import { Link } from "react-router-dom";

import AllocationDonut from "../components/AllocationDonut";
import TickerAvatar from "../components/TickerAvatar";
import { api } from "../lib/api";
import { formatPct, formatPrice, formatSigned, toneClass } from "../lib/format";
import { usePolling } from "../lib/useFetch";

const REFRESH_MS = 60_000;

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[0.8125rem] text-ink-faint">{label}</div>
      <div className={`num mt-1 text-xl font-bold ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

export default function Account() {
  const portfolio = usePolling(() => api.portfolio(), REFRESH_MS, []);
  const dividends = usePolling(() => api.dividends(), REFRESH_MS * 5, []);

  const p = portfolio.data;
  const d = dividends.data;
  const positions = p?.positions ?? [];

  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 pb-10">
      {portfolio.error && (
        <div className="rounded-xl bg-up-soft px-4 py-3 text-sm text-up">
          계좌 정보를 불러오지 못했어요: {portfolio.error}
        </div>
      )}

      <section className="card p-6">
        <div className="text-[0.9375rem] font-semibold text-ink-muted">내 총자산</div>
        <div className="num mt-1.5 text-[2.25rem] font-bold leading-tight">
          {p ? formatPrice(p.total_value, 0) : "—"}
        </div>
        {p && (
          <div className={`num mt-1 text-[0.9375rem] font-semibold ${toneClass(p.unrealized_pl)}`}>
            {formatSigned(p.unrealized_pl, 0)} ({formatPct(p.unrealized_pl_pct)})
          </div>
        )}

        <div className="mt-6 grid grid-cols-2 gap-6 md:grid-cols-4">
          <Stat label="평가금액" value={p ? formatPrice(p.market_value, 0) : "—"} />
          <Stat label="매입금액" value={p ? formatPrice(p.total_cost, 0) : "—"} />
          <Stat label="예수금" value={p ? formatPrice(p.cash, 0) : "—"} />
          <Stat
            label="연 배당 예상"
            value={d ? formatPrice(d.projected_annual_income, 0) : "—"}
            tone="text-up"
          />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_400px]">
        <section className="card overflow-hidden">
          <h2 className="px-5 pb-3 pt-5 text-[1.0625rem] font-bold">보유 종목</h2>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse">
              <thead>
                <tr className="text-[0.8125rem] text-ink-faint">
                  <th className="py-2 pl-5 text-left font-medium">종목</th>
                  <th className="py-2 pr-6 text-right font-medium">보유</th>
                  <th className="py-2 pr-6 text-right font-medium">평균단가</th>
                  <th className="py-2 pr-6 text-right font-medium">현재가</th>
                  <th className="py-2 pr-6 text-right font-medium">평가손익</th>
                  <th className="py-2 pr-5 text-right font-medium">비중</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr key={pos.symbol} className="transition-colors hover:bg-hover">
                    <td className="py-3 pl-5">
                      <Link
                        to={`/stock/${encodeURIComponent(pos.symbol)}`}
                        className="flex items-center gap-2.5 hover:underline"
                      >
                        <TickerAvatar symbol={pos.symbol} name={pos.symbol} />
                        <span className="text-[0.9375rem] font-semibold">{pos.symbol}</span>
                      </Link>
                    </td>
                    <td className="num py-3 pr-6 text-right text-sm">{pos.quantity}</td>
                    <td className="num py-3 pr-6 text-right text-sm text-ink-muted">
                      {formatPrice(pos.avg_cost, 0)}
                    </td>
                    <td className="num py-3 pr-6 text-right text-[0.9375rem] font-semibold">
                      {pos.last_price == null ? "—" : formatPrice(pos.last_price, 0)}
                    </td>
                    <td className={`num py-3 pr-6 text-right ${toneClass(pos.unrealized_pl)}`}>
                      {pos.unrealized_pl == null ? (
                        <span className="text-ink-faint">미평가</span>
                      ) : (
                        <>
                          <div className="text-[0.9375rem] font-semibold">
                            {formatSigned(pos.unrealized_pl, 0)}
                          </div>
                          <div className="text-2xs font-semibold">
                            {formatPct(pos.unrealized_pl_pct ?? 0)}
                          </div>
                        </>
                      )}
                    </td>
                    <td className="num py-3 pr-5 text-right text-sm text-ink-muted">
                      {pos.weight == null ? "—" : `${pos.weight.toFixed(1)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!portfolio.loading && positions.length === 0 && (
            <p className="px-5 py-12 text-center text-sm text-ink-faint">
              보유 종목이 없어요. POST /api/v1/portfolio/lots 로 보유 내역을 추가해 보세요.
            </p>
          )}
        </section>

        <div className="flex flex-col gap-4">
          <section className="card p-5">
            <h2 className="pb-4 text-[1.0625rem] font-bold">포트폴리오 비중</h2>
            <AllocationDonut positions={positions} />
          </section>

          <section className="card p-5">
            <h2 className="pb-4 text-[1.0625rem] font-bold">배당</h2>
            <div className="grid grid-cols-2 gap-5">
              <Stat label="최근 12개월 수령" value={d ? formatPrice(d.trailing_12m_income, 0) : "—"} />
              <Stat label="연 예상 배당" value={d ? formatPrice(d.projected_annual_income, 0) : "—"} />
              <Stat
                label="배당수익률"
                value={d ? `${d.portfolio_yield_pct.toFixed(2)}%` : "—"}
              />
              <Stat
                label="매입가 대비 수익률"
                value={d ? `${d.yield_on_cost_pct.toFixed(2)}%` : "—"}
              />
            </div>
            <p className="mt-4 text-2xs leading-relaxed text-ink-faint">
              연 예상 배당은 최근 12개월 지급액이 반복된다고 가정한 값이에요. 증배 종목은 과소,
              감배 종목은 과대 추정됩니다.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
