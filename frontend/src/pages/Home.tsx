import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import CalendarCard from "../components/CalendarCard";
import IndexGrid from "../components/IndexGrid";
import MoversTable from "../components/MoversTable";
import PreviewPanel from "../components/PreviewPanel";
import SectorTable from "../components/SectorTable";
import TickerBar from "../components/TickerBar";
import WatchlistRail from "../components/WatchlistRail";
import { api } from "../lib/api";
import { formatTime } from "../lib/format";
import type {
  Currency,
  IndexQuote,
  MarketFilter,
  MoverRow,
  SortKey,
} from "../lib/types";
import { usePolling } from "../lib/useFetch";
import { useLivePrices } from "../lib/useLivePrices";

// Quotes are ~15 minutes delayed and the server caches for 60s, so polling
// faster than this just burns requests for identical data.
const REFRESH_MS = 60_000;
const CALENDAR_REFRESH_MS = 30 * 60_000;

const SORTERS: Record<SortKey, (a: MoverRow, b: MoverRow) => number> = {
  turnover: (a, b) => (b.turnover ?? 0) - (a.turnover ?? 0),
  volume: (a, b) => (b.volume ?? 0) - (a.volume ?? 0),
  market_cap: (a, b) => (b.market_cap ?? 0) - (a.market_cap ?? 0),
  gainers: (a, b) => b.change_pct - a.change_pct,
  losers: (a, b) => a.change_pct - b.change_pct,
};

type Tab = "movers" | "sectors";

interface Props {
  onRowsChange: (rows: MoverRow[]) => void;
  onView: (symbol: string) => void;
}

export default function Home({ onRowsChange, onView }: Props) {
  const [market, setMarket] = useState<MarketFilter>("all");
  const [sortBy, setSortBy] = useState<SortKey>("turnover");
  const [tab, setTab] = useState<Tab>("movers");
  const [currency, setCurrency] = useState<Currency>("KRW");
  const [hideLeveraged, setHideLeveraged] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState(true);

  const board = usePolling(() => api.board("all", "turnover", 100), REFRESH_MS, []);
  const watchlist = usePolling(() => api.watchlist(), REFRESH_MS, []);
  const sectors = usePolling(() => api.sectors(market), REFRESH_MS, [market]);
  const calendar = usePolling(() => api.calendar(), CALENDAR_REFRESH_MS, []);
  const live = useLivePrices();

  // Hold the last non-empty response. An empty board is almost always a
  // transient upstream failure, and replacing a populated table with nothing
  // is strictly worse than showing slightly stale rows.
  const lastGood = useRef<{ indices: IndexQuote[]; movers: MoverRow[] }>({
    indices: [],
    movers: [],
  });

  if (board.data?.indices.length) lastGood.current.indices = board.data.indices;
  if (board.data?.movers.length) lastGood.current.movers = board.data.movers;

  const indices = board.data?.indices.length ? board.data.indices : lastGood.current.indices;
  const baseMovers = board.data?.movers.length ? board.data.movers : lastGood.current.movers;
  const degraded = Boolean(board.data && board.data.movers.length === 0);

  const usdkrw = useMemo(
    () => indices.find((q) => q.key === "usdkrw")?.price ?? null,
    [indices],
  );

  const boardRefreshRef = useRef(board.refresh);
  boardRefreshRef.current = board.refresh;

  useEffect(() => {
    if (!degraded) return;
    const id = window.setTimeout(() => boardRefreshRef.current(), 4_000);
    return () => window.clearTimeout(id);
  }, [degraded, board.data]);

  // Ranking is computed from the REST snapshot only, so it changes when the
  // board refreshes rather than on every tick. Re-sorting live would make rows
  // jump around the screen continuously and force a full DOM reorder.
  const ordered = useMemo(() => {
    let filtered = market === "all" ? baseMovers : baseMovers.filter((r) => r.market === market);
    if (hideLeveraged) filtered = filtered.filter((r) => !r.leveraged);
    return [...filtered].sort(SORTERS[sortBy]).map((row, i) => ({ ...row, rank: i + 1 }));
  }, [baseMovers, market, sortBy, hideLeveraged]);

  // Reuse the previous object when a symbol's price hasn't moved. Identical
  // references let React.memo skip rows that didn't change.
  const mergeCache = useRef(new Map<string, { key: string; row: MoverRow }>());

  const rows = useMemo(() => {
    return ordered.map((row) => {
      const tick = live.prices[row.symbol];
      if (!tick) return row;

      const key = `${row.rank}|${tick.price}|${row.volume}|${tick.delayed}`;
      const cached = mergeCache.current.get(row.symbol);
      if (cached?.key === key) return cached.row;

      const merged: MoverRow = {
        ...row,
        price: tick.price,
        change: tick.change ?? row.change,
        change_pct: tick.change_pct ?? row.change_pct,
        turnover: row.volume ? tick.price * row.volume : row.turnover,
        live: !tick.delayed,
      };

      mergeCache.current.set(row.symbol, { key, row: merged });
      return merged;
    });
  }, [ordered, live.prices]);

  // Publish rows upward so the search overlay can index them.
  useEffect(() => onRowsChange(rows), [rows, onRowsChange]);

  const watchEntries = useMemo(
    () =>
      (watchlist.data?.entries ?? []).map((entry) => {
        const tick = live.prices[entry.symbol];
        return tick
          ? {
              ...entry,
              price: tick.price,
              change: tick.change ?? entry.change,
              change_pct: tick.change_pct ?? entry.change_pct,
            }
          : entry;
      }),
    [watchlist.data, live.prices],
  );

  const watched = useMemo(
    () => new Set((watchlist.data?.entries ?? []).map((e) => e.symbol)),
    [watchlist.data],
  );

  // Read mutable state through refs so these callbacks keep a stable identity.
  // A new function each render would defeat React.memo on every table row.
  const watchedRef = useRef(watched);
  watchedRef.current = watched;
  const refreshRef = useRef(watchlist.refresh);
  refreshRef.current = watchlist.refresh;

  const toggleWatch = useCallback(async (symbol: string) => {
    if (watchedRef.current.has(symbol)) await api.removeFromWatchlist(symbol);
    else await api.addToWatchlist(symbol);
    refreshRef.current();
  }, []);

  const removeWatch = useCallback(async (symbol: string) => {
    await api.removeFromWatchlist(symbol);
    refreshRef.current();
  }, []);

  const onViewRef = useRef(onView);
  onViewRef.current = onView;

  const select = useCallback((symbol: string) => {
    setSelected(symbol);
    onViewRef.current(symbol);
  }, []);

  const selectedRow = useMemo(
    () => rows.find((r) => r.symbol === selected) ?? null,
    [rows, selected],
  );

  // Placeholder for the LLM summary in roadmap Phase 4. Derived, not invented.
  const headline = useMemo(() => {
    if (rows.length === 0) return null;
    const top = [...rows].sort((a, b) => b.change_pct - a.change_pct)[0];
    const advancing = rows.filter((m) => m.change_pct > 0).length;
    return `${top.name} ${top.change_pct > 0 ? "상승" : "하락"} 주도 · 추적 종목 ${rows.length}개 중 ${advancing}개 상승`;
  }, [rows]);

  const liveCount = rows.filter((r) => r.live).length;

  return (
    <div className="flex min-h-0 flex-1">
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-1 flex-col gap-4 px-6 pb-6">
          <div className="flex items-center gap-5 text-[0.8125rem]">
            <span className="flex items-center gap-1.5 text-ink-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-[#26A96C]" />
              국내 정규장 09:00 ~ 15:30
            </span>
            <span className="flex items-center gap-1.5 text-ink-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-[#26A96C]" />
              해외 데이마켓 09:00 ~ 17:00
            </span>

            <button
              type="button"
              onClick={() => setSummaryOpen((open) => !open)}
              className="ml-auto text-ink-faint transition-colors hover:text-ink-muted"
            >
              {summaryOpen ? "요약 접기" : "요약 펼치기"}
            </button>
          </div>

          {board.error && (
            <div className="rounded-xl bg-up-soft px-4 py-3 text-sm text-up">
              시세를 불러오지 못했어요: {board.error}
            </div>
          )}

          {degraded && !board.error && (
            <div className="rounded-xl bg-down-soft px-4 py-3 text-sm text-down">
              시세 서버가 준비 중이에요. 잠시 후 자동으로 다시 불러올게요.
            </div>
          )}

          {/* items-start so the index grid keeps its natural height instead of
              stretching to match a taller calendar card and leaving dead space. */}
          {summaryOpen && (
            <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
              <IndexGrid indices={indices} loading={board.loading} />
              <CalendarCard calendar={calendar.data} loading={calendar.loading} />
            </div>
          )}

          <section className="card overflow-hidden">
            <div className="flex items-center gap-4 px-5 pt-5">
              <button
                type="button"
                onClick={() => setTab("movers")}
                className={`text-[1.0625rem] font-bold transition-colors ${
                  tab === "movers" ? "text-ink" : "text-ink-faint hover:text-ink-muted"
                }`}
              >
                실시간 차트
              </button>
              <button
                type="button"
                onClick={() => setTab("sectors")}
                className={`text-[1.0625rem] font-bold transition-colors ${
                  tab === "sectors" ? "text-ink" : "text-ink-faint hover:text-ink-muted"
                }`}
              >
                지금 뜨는 산업
              </button>

              <span className="ml-auto text-[0.8125rem]">
                {live.connected ? (
                  <span className="flex items-center gap-1.5 text-ink-muted">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#26A96C]" />
                    실시간 {liveCount}종목
                    {rows.length > liveCount && (
                      <span className="text-ink-faint">
                        · 지연 {rows.length - liveCount}종목
                      </span>
                    )}
                  </span>
                ) : (
                  <span className="text-ink-faint">
                    {board.data ? `${formatTime(board.data.as_of)} 기준 · 지연 시세` : "지연 시세"}
                  </span>
                )}
              </span>
            </div>

            {tab === "movers" ? (
              <div className="flex">
                <MoversTable
                  rows={rows}
                  loading={board.loading}
                  market={market}
                  sortBy={sortBy}
                  onMarketChange={setMarket}
                  onSortChange={setSortBy}
                  watched={watched}
                  onToggleWatch={toggleWatch}
                  flash={live.flash}
                  currency={currency}
                  usdkrw={usdkrw}
                  hideLeveraged={hideLeveraged}
                  onHideLeveragedChange={setHideLeveraged}
                  selected={selected}
                  onSelect={select}
                />
                {/* Sticky so the preview stays in view while the table scrolls. */}
                <div className="hidden w-[360px] shrink-0 border-l border-line xl:block">
                  <div className="sticky top-20">
                    <PreviewPanel row={selectedRow} currency={currency} usdkrw={usdkrw} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="pt-3">
                <SectorTable sectors={sectors.data ?? []} loading={sectors.loading} />
              </div>
            )}
          </section>
        </div>

        <TickerBar indices={indices} />
      </main>

      <WatchlistRail
        entries={watchEntries}
        loading={watchlist.loading}
        onRemove={removeWatch}
        headline={headline}
        currency={currency}
        usdkrw={usdkrw}
        onCurrencyChange={setCurrency}
      />
    </div>
  );
}
