import { memo } from "react";

import { formatPct, formatPrice, formatSigned, toneClass, toneStroke } from "../lib/format";
import type { IndexQuote } from "../lib/types";
import Sparkline from "./Sparkline";

function IndexCard({ quote }: { quote: IndexQuote }) {
  const tone = toneClass(quote.change);

  return (
    <button
      type="button"
      className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-hover"
    >
      <Sparkline values={quote.sparkline} stroke={toneStroke(quote.change)} width={88} height={40} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-ink-muted">{quote.label}</div>
        <div className="mt-0.5 flex items-baseline gap-1.5">
          <span className="num text-[1.0625rem] font-bold">
            {formatPrice(quote.price, quote.decimals, "")}
          </span>
          <span className={`num text-[0.8125rem] font-semibold ${tone}`}>
            {formatSigned(quote.change, quote.decimals)} ({formatPct(quote.change_pct)})
          </span>
        </div>
      </div>
    </button>
  );
}

// Index cards come from the REST board, not the tick stream — memoizing keeps
// their sparklines from re-rendering on every price update elsewhere.
export default memo(function IndexGrid({
  indices,
  loading,
}: {
  indices: IndexQuote[];
  loading: boolean;
}) {
  if (loading && indices.length === 0) {
    return (
      <div className="card grid grid-cols-1 gap-1 p-3 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-raised/50" />
        ))}
      </div>
    );
  }

  // "ticker"-group entries are intentionally excluded — they render in the bar.
  const columns = [
    indices.filter((q) => q.group === "domestic"),
    indices.filter((q) => q.group === "macro"),
    indices.filter((q) => q.group === "global"),
  ];

  return (
    <section className="card grid grid-cols-1 gap-x-3 gap-y-1 p-3 md:grid-cols-2 xl:grid-cols-3">
      {columns.map((group, i) => (
        <div key={i} className="flex flex-col gap-1">
          {group.map((quote) => (
            <IndexCard key={quote.key} quote={quote} />
          ))}
        </div>
      ))}
    </section>
  );
});
