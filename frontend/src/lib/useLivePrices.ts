import { useEffect, useRef, useState } from "react";

export interface LivePrice {
  symbol: string;
  price: number;
  change: number | null;
  change_pct: number | null;
  delayed: boolean;
}

export type FlashDirection = "up" | "down";

interface LiveState {
  prices: Record<string, LivePrice>;
  flash: Record<string, FlashDirection>;
  connected: boolean;
}

const FLASH_MS = 700;
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;

// Ticks arrive faster than a screen can usefully show them. Buffering and
// flushing on a fixed cadence turns a burst of 40 messages into one render;
// without this, every message re-rendered the whole page and the UI fell behind.
const FLUSH_MS = 250;

function socketUrl(): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/api/v1/ws/prices`;
}

/**
 * Subscribes to the server's price stream.
 *
 * The server sends one `snapshot` on connect, then individual `tick` messages.
 * Reconnects with backoff — Yahoo's upstream socket drops routinely, and the
 * server restarting during development shouldn't leave the page permanently dead.
 */
export function useLivePrices(): LiveState {
  const [state, setState] = useState<LiveState>({
    prices: {},
    flash: {},
    connected: false,
  });

  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);
  const flushRef = useRef<number | null>(null);
  const pending = useRef<Map<string, LivePrice>>(new Map());
  const flashUntil = useRef<Map<string, number>>(new Map());
  const closedByUs = useRef(false);

  useEffect(() => {
    closedByUs.current = false;
    let backoff = RECONNECT_BASE_MS;

    const flush = () => {
      if (pending.current.size === 0) {
        // Still expire any flashes whose window has closed.
        const now = Date.now();
        if ([...flashUntil.current.values()].every((until) => until > now)) return;
      }

      const batch = new Map(pending.current);
      pending.current.clear();

      setState((prev) => {
        const prices = { ...prev.prices };
        const flash = { ...prev.flash };
        const now = Date.now();

        for (const [symbol, incoming] of batch) {
          const previous = prices[symbol];
          prices[symbol] = incoming;

          if (previous && previous.price !== incoming.price) {
            flash[symbol] = incoming.price > previous.price ? "up" : "down";
            flashUntil.current.set(symbol, now + FLASH_MS);
          }
        }

        for (const [symbol, until] of flashUntil.current) {
          if (until <= now) {
            delete flash[symbol];
            flashUntil.current.delete(symbol);
          }
        }

        return { ...prev, prices, flash };
      });
    };

    flushRef.current = window.setInterval(flush, FLUSH_MS);

    // Newest wins: if a symbol ticks five times inside one window, only the
    // last price matters — the intermediate ones were never rendered anyway.
    const applyTick = (incoming: LivePrice) => {
      pending.current.set(incoming.symbol, incoming);
    };

    const connect = () => {
      if (closedByUs.current) return;

      const socket = new WebSocket(socketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        backoff = RECONNECT_BASE_MS;
        setState((prev) => ({ ...prev, connected: true }));
      };

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "snapshot") {
          setState((prev) => ({ ...prev, prices: message.prices ?? {} }));
        } else if (message.type === "tick") {
          applyTick(message.price as LivePrice);
        }
        // heartbeats need no handling; they exist to keep the socket open
      };

      socket.onclose = () => {
        setState((prev) => ({ ...prev, connected: false }));
        if (closedByUs.current) return;
        timerRef.current = window.setTimeout(connect, backoff);
        backoff = Math.min(backoff * 2, RECONNECT_MAX_MS);
      };

      socket.onerror = () => socket.close();
    };

    connect();

    return () => {
      closedByUs.current = true;
      if (timerRef.current) window.clearTimeout(timerRef.current);
      if (flushRef.current) window.clearInterval(flushRef.current);
      pending.current.clear();
      flashUntil.current.clear();
      socketRef.current?.close();
    };
  }, []);

  return state;
}
