import { useCallback, useMemo, useState } from "react";

import IndexGrid from "../components/IndexGrid";
import MoversTable from "../components/MoversTable";
import TickerBar from "../components/TickerBar";
import WatchlistRail from "../components/WatchlistRail";
import { api } from "../lib/api";
import { formatTime } from "../lib/format";
import type { MarketFilter, SortKey } from "../lib/types";
import { usePolling } from "../lib/useFetch";

const REFRESH_MS = 30_000;

export default function Home() {
  const [market, setMarket] = useState<MarketFilter>("all");
  const [sortBy, setSortBy] = useState<SortKey>("turnover");

  const board = usePolling(() => api.board(market, sortBy), REFRESH_MS, [market, sortBy]);
  const watchlist = usePolling(() => api.watchlist(), REFRESH_MS, []);

  const watched = useMemo(
    () => new Set((watchlist.data?.entries ?? []).map((e) => e.symbol)),
    [watchlist.data],
  );

  const toggleWatch = useCallback(
    async (symbol: string) => {
      if (watched.has(symbol)) await api.removeFromWatchlist(symbol);
      else await api.addToWatchlist(symbol);
      watchlist.refresh();
    },
    [watched, watchlist],
  );

  const removeWatch = useCallback(
    async (symbol: string) => {
      await api.removeFromWatchlist(symbol);
      watchlist.refresh();
    },
    [watchlist],
  );

  // Placeholder for the LLM summary in roadmap Phase 4. Derived, not invented.
  const headline = useMemo(() => {
    const movers = board.data?.movers ?? [];
    if (movers.length === 0) return null;
    const top = [...movers].sort((a, b) => b.change_pct - a.change_pct)[0];
    const advancing = movers.filter((m) => m.change_pct > 0).length;
    return `${top.name} ${top.change_pct > 0 ? "상승" : "하락"} 주도 · 추적 종목 ${movers.length}개 중 ${advancing}개 상승`;
  }, [board.data]);

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
          </div>

          {board.error && (
            <div className="rounded-xl bg-up-soft px-4 py-3 text-sm text-up">
              시세를 불러오지 못했어요: {board.error}
            </div>
          )}

          <IndexGrid indices={board.data?.indices ?? []} loading={board.loading} />

          <MoversTable
            rows={board.data?.movers ?? []}
            loading={board.loading}
            market={market}
            sortBy={sortBy}
            onMarketChange={setMarket}
            onSortChange={setSortBy}
            watched={watched}
            onToggleWatch={toggleWatch}
            asOf={board.data ? formatTime(board.data.as_of) : null}
          />
        </div>

        <TickerBar indices={board.data?.indices ?? []} />
      </main>

      <WatchlistRail
        entries={watchlist.data?.entries ?? []}
        loading={watchlist.loading}
        onRemove={removeWatch}
        headline={headline}
      />
    </div>
  );
}
