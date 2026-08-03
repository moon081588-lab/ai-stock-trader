import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { MoverRow } from "../lib/types";
import TickerAvatar from "./TickerAvatar";

interface Props {
  open: boolean;
  onClose: () => void;
  rows: MoverRow[];
  recent: string[];
}

/** Matches on Korean name, ticker, and sector — people search all three. */
function score(row: MoverRow, query: string): number {
  const q = query.toLowerCase();
  const name = row.name.toLowerCase();
  const symbol = row.symbol.toLowerCase();

  if (symbol === q || name === q) return 0;
  if (symbol.startsWith(q) || name.startsWith(q)) return 1;
  if (symbol.includes(q) || name.includes(q)) return 2;
  if (row.sector.toLowerCase().includes(q)) return 3;
  return Number.POSITIVE_INFINITY;
}

export default function SearchOverlay({ open, onClose, rows, recent }: Props) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setCursor(0);
      inputRef.current?.focus();
    }
  }, [open]);

  const results = useMemo(() => {
    if (!query.trim()) {
      const bySymbol = new Map(rows.map((r) => [r.symbol, r]));
      return recent.map((s) => bySymbol.get(s)).filter((r): r is MoverRow => Boolean(r));
    }
    return rows
      .map((row) => ({ row, rank: score(row, query.trim()) }))
      .filter((r) => Number.isFinite(r.rank))
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 8)
      .map((r) => r.row);
  }, [query, rows, recent]);

  if (!open) return null;

  const go = (symbol: string) => {
    onClose();
    navigate(`/stock/${encodeURIComponent(symbol)}`);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") return onClose();
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCursor((c) => Math.min(c + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (event.key === "Enter" && results[cursor]) {
      go(results[cursor].symbol);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[12vh]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-xl2 bg-surface shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setCursor(0);
          }}
          onKeyDown={onKeyDown}
          placeholder="종목명 · 티커 · 업종으로 검색"
          className="w-full bg-transparent px-5 py-4 text-[1.0625rem] outline-none placeholder:text-ink-faint"
        />

        <div className="max-h-[50vh] overflow-y-auto border-t border-line p-2">
          {!query.trim() && results.length > 0 && (
            <div className="px-3 py-2 text-2xs text-ink-faint">최근 본 종목</div>
          )}

          {results.map((row, i) => (
            <button
              key={row.symbol}
              type="button"
              onMouseEnter={() => setCursor(i)}
              onClick={() => go(row.symbol)}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left ${
                i === cursor ? "bg-hover" : ""
              }`}
            >
              <TickerAvatar symbol={row.symbol} name={row.name} size={30} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.9375rem] font-semibold">
                  {row.name}
                </span>
                <span className="block text-2xs text-ink-faint">
                  {row.symbol} · {row.sector}
                </span>
              </span>
              <span className="text-2xs text-ink-faint">{row.market}</span>
            </button>
          ))}

          {query.trim() && results.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-ink-faint">
              추적 중인 종목에서 찾지 못했어요
            </p>
          )}
          {!query.trim() && results.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-ink-faint">
              종목명이나 티커를 입력해 보세요
            </p>
          )}
        </div>

        <div className="flex items-center gap-3 border-t border-line px-4 py-2 text-2xs text-ink-faint">
          <span>↑↓ 이동</span>
          <span>↵ 열기</span>
          <span>esc 닫기</span>
        </div>
      </div>
    </div>
  );
}
