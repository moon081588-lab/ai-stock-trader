// Mirrors app/models/schemas.py. Keep in sync when the backend contract changes.

export interface IndexQuote {
  key: string;
  label: string;
  symbol: string;
  /** "ticker" entries render only in the bottom bar, never as a card. */
  group: "domestic" | "global" | "macro" | "ticker";
  price: number;
  change: number;
  change_pct: number;
  unit: string;
  decimals: number;
  sparkline: number[];
}

export interface MoverRow {
  rank: number;
  symbol: string;
  name: string;
  market: "KR" | "US";
  kind: "stock" | "etf";
  price: number;
  change: number;
  change_pct: number;
  sector: string;
  leveraged: boolean;
  volume: number | null;
  turnover: number | null;
  market_cap: number | null;
  /** Set client-side once a live tick has been merged in. */
  live?: boolean;
}

export interface SectorPerformance {
  sector: string;
  change_pct: number;
  count: number;
  turnover: number | null;
  leader_symbol: string;
  leader_name: string;
  leader_change_pct: number;
}

export interface EarningsEvent {
  symbol: string;
  name: string;
  market: "KR" | "US";
  event_date: string;
  days_away: number;
}

export interface CalendarView {
  events: EarningsEvent[];
  note: string;
}

/** Display currency. Prices are stored in their native currency and converted. */
export type Currency = "KRW" | "USD";

export interface MarketBoard {
  as_of: string;
  indices: IndexQuote[];
  movers: MoverRow[];
  stale: boolean;
}

export interface WatchlistEntry {
  symbol: string;
  name: string;
  market: "KR" | "US";
  price: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface WatchlistView {
  entries: WatchlistEntry[];
}

export interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  last_price: number | null;
  market_value: number | null;
  unrealized_pl: number | null;
  unrealized_pl_pct: number | null;
  weight: number | null;
}

export interface PortfolioSummary {
  cash: number;
  positions: Position[];
  market_value: number;
  total_value: number;
  total_cost: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
}

export interface DividendSummary {
  trailing_12m_income: number;
  projected_annual_income: number;
  portfolio_yield_pct: number;
  yield_on_cost_pct: number;
  by_symbol: Record<string, number>;
}

export interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type ForecastMethod = "drift" | "monte_carlo" | "linear_trend";

export interface ForecastPoint {
  horizon_days: number;
  expected_price: number;
  low: number;
  high: number;
  confidence: number;
}

export interface Forecast {
  symbol: string;
  method: ForecastMethod;
  last_price: number;
  points: ForecastPoint[];
  annualized_volatility: number;
  expected_return_pct: number;
  disclaimer: string;
}

export interface RiskMetrics {
  cagr_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  annualized_volatility_pct: number;
  value_at_risk_95_pct: number;
}

export interface StockDetail {
  symbol: string;
  name: string;
  market: "KR" | "US";
  kind: "stock" | "etf";
  price: number;
  change: number;
  change_pct: number;
  bars: Bar[];
  forecast: Forecast;
  metrics: RiskMetrics;
}

export interface NewsItem {
  symbol: string;
  headline: string;
  url: string | null;
  source: string | null;
  published_at: string | null;
  sentiment: number;
}

export interface NewsSummary {
  symbol: string;
  item_count: number;
  average_sentiment: number;
  items: NewsItem[];
}

export type MarketFilter = "all" | "KR" | "US";
export type SortKey = "turnover" | "volume" | "market_cap" | "gainers" | "losers";
