import { useCallback, useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";

import IconRail from "./components/IconRail";
import SearchOverlay from "./components/SearchOverlay";
import TopNav from "./components/TopNav";
import type { MoverRow } from "./lib/types";
import { useRecentlyViewed } from "./lib/useRecentlyViewed";
import Account from "./pages/Account";
import Home from "./pages/Home";
import StockDetail from "./pages/StockDetail";

export default function App() {
  const [searchOpen, setSearchOpen] = useState(false);
  // Home publishes its rows up so search can index them without refetching.
  const [rows, setRows] = useState<MoverRow[]>([]);
  const { symbols: recent, remember } = useRecentlyViewed();

  const openSearch = useCallback(() => setSearchOpen(true), []);
  const closeSearch = useCallback(() => setSearchOpen(false), []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if (typing) return;
      if (event.key === "/") {
        event.preventDefault();
        setSearchOpen(true);
      } else if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setSearchOpen(true);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="flex h-full flex-col">
      <TopNav onOpenSearch={openSearch} />

      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <Routes>
            <Route path="/" element={<Home onRowsChange={setRows} onView={remember} />} />
            <Route path="/account" element={<Account />} />
            <Route path="/stock/:symbol" element={<StockDetail onView={remember} />} />
            <Route
              path="*"
              element={
                <main className="grid flex-1 place-items-center text-ink-faint">
                  페이지를 찾을 수 없어요
                </main>
              }
            />
          </Routes>
        </div>

        <IconRail recentCount={recent.length} onOpenRecent={openSearch} />
      </div>

      <SearchOverlay open={searchOpen} onClose={closeSearch} rows={rows} recent={recent} />
    </div>
  );
}
