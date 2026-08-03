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
      {/* shrink-0: the sparkline must never be squeezed into the numbers */}
      <span className="shrink-0">
        <Sparkline
          values={quote.sparkline}
          stroke={toneStroke(quote.change)}
          width={72}
          height={40}
        />
      </span>

      {/* Price and change stack rather than sitting inline. Side by side they
          overflowed once the calendar card took 320px off this row's width. */}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[0.8125rem] font-semibold text-ink-muted">
          {quote.label}
        </span>
        <span className="num block whitespace-nowrap text-[1.0625rem] font-bold leading-tight">
          {formatPrice(quote.price, quote.decimals, "")}
        </span>
        <span className={`num block whitespace-nowrap text-2xs font-semibold ${tone}`}>
          {formatSigned(quote.change, quote.decimals)} ({formatPct(quote.change_pct)})
        </span>
      </span>
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
      <div className="card grid grid-cols-1 gap-1 p-3 sm:grid-cols-2 2xl:grid-cols-3">
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
  ].filter((column) => column.length > 0);

  return (
    <section className="card grid grid-cols-1 gap-x-3 gap-y-1 self-start p-3 sm:grid-cols-2 2xl:grid-cols-3">
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
