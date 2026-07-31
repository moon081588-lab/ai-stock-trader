import type { NewsSummary } from "../lib/types";

function sentimentLabel(score: number): { text: string; className: string } {
  if (score > 0.2) return { text: "긍정", className: "bg-up-soft text-up" };
  if (score < -0.2) return { text: "부정", className: "bg-down-soft text-down" };
  return { text: "중립", className: "bg-raised text-ink-muted" };
}

export default function NewsFeed({
  news,
  loading,
}: {
  news: NewsSummary | null;
  loading: boolean;
}) {
  if (loading && !news) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-raised/50" />
        ))}
      </div>
    );
  }

  if (!news || news.items.length === 0) {
    return <p className="py-8 text-center text-sm text-ink-faint">관련 뉴스를 찾지 못했어요</p>;
  }

  const overall = sentimentLabel(news.average_sentiment);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2 pb-2">
        <span className={`rounded-md px-2 py-1 text-2xs font-semibold ${overall.className}`}>
          전체 {overall.text}
        </span>
        <span className="num text-2xs text-ink-faint">
          {news.item_count}건 · 평균 {news.average_sentiment.toFixed(2)}
        </span>
      </div>

      {news.items.map((item, i) => {
        const tone = sentimentLabel(item.sentiment);
        return (
          <a
            key={`${item.headline}-${i}`}
            href={item.url ?? undefined}
            target="_blank"
            rel="noreferrer noopener"
            className="flex items-start gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-hover"
          >
            <span
              className={`mt-0.5 shrink-0 rounded-md px-1.5 py-0.5 text-2xs font-semibold ${tone.className}`}
            >
              {tone.text}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[0.875rem] leading-snug">{item.headline}</span>
              {item.source && (
                <span className="mt-0.5 block text-2xs text-ink-faint">{item.source}</span>
              )}
            </span>
          </a>
        );
      })}

      <p className="mt-2 px-2 text-2xs leading-relaxed text-ink-faint">
        감성 점수는 헤드라인 단어 사전 기반이에요. 본문을 읽지 않으므로 반어법이나 맥락은
        놓칩니다.
      </p>
    </div>
  );
}
