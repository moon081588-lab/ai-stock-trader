import { useCallback, useEffect, useRef, useState } from "react";

interface State<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Fetch on mount and re-fetch on an interval.
 *
 * Keeps the previous `data` while refreshing so the table doesn't flash empty
 * every poll — a visible flicker every 30s reads as broken.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  deps: unknown[] = [],
): State<T> & { refresh: () => void } {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: true });
  const mounted = useRef(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fetcher, deps);

  const load = useCallback(async () => {
    try {
      const data = await run();
      if (mounted.current) setState({ data, error: null, loading: false });
    } catch (err) {
      if (mounted.current) {
        setState((prev) => ({
          data: prev.data,
          error: err instanceof Error ? err.message : "요청에 실패했어요",
          loading: false,
        }));
      }
    }
  }, [run]);

  useEffect(() => {
    mounted.current = true;
    setState((prev) => ({ ...prev, loading: prev.data === null }));
    void load();

    const id = window.setInterval(load, intervalMs);
    return () => {
      mounted.current = false;
      window.clearInterval(id);
    };
  }, [load, intervalMs]);

  return { ...state, refresh: load };
}
