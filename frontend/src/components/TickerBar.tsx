import { memo } from "react";

import { formatPct, formatPrice, formatSigned, toneClass } from "../lib/format";
import type { IndexQuote } from "../lib/types";

export default memo(function TickerBar({ indices }: { indices: IndexQuote[] }) {
  const global = indices.filter((q) => q.group === "global");

  return (
    <footer className="sticky bottom-0 z-20 flex items-center gap-6 border-t border-line bg-base px-6 py-3 text-[0.8125rem]">
      <span className="shrink-0 font-semibold text-ink-faint">투자 유의사항</span>
      <span className="h-3.5 w-px bg-line" />

      <div className="flex min-w-0 flex-1 items-center gap-6 overflow-x-auto">
        {global.map((quote) => (
          <div key={quote.key} className="flex shrink-0 items-center gap-2">
            <span className="text-ink-muted">{quote.label}</span>
            <span className="num font-semibold">{formatPrice(quote.price, quote.decimals, "")}</span>
            <span className={`num font-semibold ${toneClass(quote.change)}`}>
              {formatSigned(quote.change, quote.decimals)} ({formatPct(quote.change_pct)})
            </span>
          </div>
        ))}
      </div>

      <span className="shrink-0 text-ink-faint">
        모든 시세는 지연되며, 투자 조언이 아닙니다
      </span>
    </footer>
  );
});
