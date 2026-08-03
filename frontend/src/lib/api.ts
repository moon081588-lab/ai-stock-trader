import type {
  CalendarView,
  DividendSummary,
  ForecastMethod,
  MarketBoard,
  MarketFilter,
  NewsSummary,
  PortfolioSummary,
  SectorPerformance,
  SortKey,
  StockDetail,
  WatchlistView,
} from "./types";

const BASE = "/api/v1";

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    // FastAPI puts the useful message in `detail`; surface it rather than "500".
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  board: (market: MarketFilter, sortBy: SortKey, limit = 30) =>
    request<MarketBoard>(
      `/market/board?market=${market}&sort_by=${sortBy}&limit=${limit}`,
    ),

  sectors: (market: MarketFilter) =>
    request<SectorPerformance[]>(`/market/sectors?market=${market}`),

  calendar: () => request<CalendarView>("/market/calendar"),

  watchlist: () => request<WatchlistView>("/watchlist"),

  addToWatchlist: (symbol: string) =>
    request<WatchlistView>(`/watchlist/${encodeURIComponent(symbol)}`, { method: "POST" }),

  removeFromWatchlist: (symbol: string) =>
    request<WatchlistView>(`/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),

  stock: (symbol: string, method: ForecastMethod, lookbackDays: number) =>
    request<StockDetail>(
      `/stocks/${encodeURIComponent(symbol)}?method=${method}&lookback_days=${lookbackDays}`,
    ),

  news: (symbol: string, limit = 12) =>
    request<NewsSummary>(`/news/${encodeURIComponent(symbol)}?limit=${limit}`),

  portfolio: () => request<PortfolioSummary>("/portfolio"),

  dividends: () => request<DividendSummary>("/portfolio/dividends"),
};

export { ApiError };
