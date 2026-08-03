/** Formatting helpers. Korean number conventions (억/조) for large figures. */

import type { Currency } from "./types";

export function formatPrice(value: number, decimals = 0, unit = "원"): string {
  return `${value.toLocaleString("ko-KR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}${unit}`;
}

export function formatSigned(value: number, decimals = 0, unit = ""): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toLocaleString("ko-KR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}${unit}`;
}

export function formatPct(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(2)}%`;
}

/** 1_237_00000000 -> "1,237억원". Matches how Korean brokerages show turnover. */
export function formatKrwCompact(value: number | null): string {
  if (value == null) return "—";
  const JO = 1e12;
  const EOK = 1e8;
  if (Math.abs(value) >= JO) return `${(value / JO).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}조원`;
  if (Math.abs(value) >= EOK) return `${Math.round(value / EOK).toLocaleString("ko-KR")}억원`;
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}

export function formatVolume(value: number | null): string {
  if (value == null) return "—";
  if (value >= 1e8) return `${(value / 1e8).toFixed(1)}억`;
  if (value >= 1e4) return `${Math.round(value / 1e4).toLocaleString("ko-KR")}만`;
  return Math.round(value).toLocaleString("ko-KR");
}

/** Red for up, blue for down — Korean market convention. */
export function toneClass(value: number | null | undefined): string {
  if (value == null || value === 0) return "text-ink-muted";
  return value > 0 ? "text-up" : "text-down";
}

export function toneStroke(value: number | null | undefined): string {
  if (value == null || value === 0) return "#6B7180";
  return value > 0 ? "#F5636E" : "#5B8DEF";
}

/**
 * Convert a native-currency price into the display currency.
 *
 * Prices arrive in whatever the listing trades in — KRW for .KS, USD for US
 * names — so conversion needs both the source market and the live USDKRW rate.
 * If we don't have a rate yet, leave the number alone rather than inventing one.
 */
export function convert(
  value: number,
  from: "KR" | "US",
  to: Currency,
  usdkrw: number | null,
): number {
  if (!usdkrw) return value;
  if (from === "KR" && to === "USD") return value / usdkrw;
  if (from === "US" && to === "KRW") return value * usdkrw;
  return value;
}

export function currencyUnit(currency: Currency): string {
  return currency === "KRW" ? "원" : "$";
}

export function currencyDecimals(currency: Currency): number {
  return currency === "KRW" ? 0 : 2;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
