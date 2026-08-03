import { memo } from "react";
import { Link } from "react-router-dom";

import type { CalendarView } from "../lib/types";

function dayLabel(daysAway: number, iso: string): string {
  if (daysAway === 0) return "오늘";
  if (daysAway === 1) return "내일";
  return `${new Date(iso).getMonth() + 1}월 ${new Date(iso).getDate()}일`;
}

/**
 * Earnings only. Toss's 주요 일정 also carries macro releases (ISM, ADP,
 * nonfarm payrolls); those need an economic-data vendor we don't have, so the
 * heading says 실적 발표 rather than implying full coverage.
 */
export default memo(function CalendarCard({
  calendar,
  loading,
}: {
  calendar: CalendarView | null;
  loading: boolean;
}) {
  const events = calendar?.events ?? [];

  return (
    <section className="card flex flex-col gap-3 p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-[0.9375rem] font-bold">실적 발표 일정</h2>
        <span className="text-2xs text-ink-faint">앞으로 45일</span>
      </div>

      {loading && events.length === 0 ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-6 animate-pulse rounded bg-raised/50" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <p className="py-3 text-sm text-ink-faint">예정된 실적 발표가 없어요</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {events.slice(0, 5).map((event) => (
            <li key={event.symbol} className="flex items-center gap-2.5">
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                  event.days_away === 0 ? "bg-[#26A96C]" : "bg-line"
                }`}
              />
              <span className="w-14 shrink-0 text-2xs text-ink-faint">
                {dayLabel(event.days_away, event.event_date)}
              </span>
              <Link
                to={`/stock/${encodeURIComponent(event.symbol)}`}
                className="min-w-0 flex-1 truncate text-[0.8125rem] hover:underline"
              >
                {event.name}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <p className="text-2xs leading-relaxed text-ink-faint">
        추적 종목의 실적 발표만 표시해요. 미국 고용지표 같은 거시 일정은 포함되지 않아요.
      </p>
    </section>
  );
});
