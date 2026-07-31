import { Route, Routes } from "react-router-dom";

import TopNav from "./components/TopNav";
import Account from "./pages/Account";
import Home from "./pages/Home";
import StockDetail from "./pages/StockDetail";

export default function App() {
  return (
    <div className="flex h-full flex-col">
      <TopNav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/account" element={<Account />} />
        <Route path="/stock/:symbol" element={<StockDetail />} />
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
  );
}
