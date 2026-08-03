import { useCallback, useEffect, useState } from "react";

const KEY = "ai-trader.recent";
const LIMIT = 8;

function read(): string[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return []; // corrupt or unavailable storage shouldn't break the page
  }
}

/** 최근 본 종목, newest first. Persisted locally — there's no user account. */
export function useRecentlyViewed() {
  const [symbols, setSymbols] = useState<string[]>(read);

  // Keep tabs in sync; storage events only fire in *other* tabs.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === KEY) setSymbols(read());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const remember = useCallback((symbol: string) => {
    setSymbols((prev) => {
      const next = [symbol, ...prev.filter((s) => s !== symbol)].slice(0, LIMIT);
      try {
        window.localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* private mode, quota — the in-memory list still works this session */
      }
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setSymbols([]);
    try {
      window.localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return { symbols, remember, clear };
}
