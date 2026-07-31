const PALETTE = [
  "#3182F6",
  "#F5636E",
  "#F2A93B",
  "#26A96C",
  "#8B5CF6",
  "#EC4899",
  "#0EA5E9",
  "#F97316",
];

/** Deterministic color per symbol — no logo assets, no third-party brand marks. */
function colorFor(symbol: string): string {
  let hash = 0;
  for (const ch of symbol) hash = (hash * 31 + ch.charCodeAt(0)) % 997;
  return PALETTE[hash % PALETTE.length];
}

export default function TickerAvatar({
  symbol,
  name,
  size = 32,
}: {
  symbol: string;
  name: string;
  size?: number;
}) {
  const initial = name.trim().charAt(0) || symbol.charAt(0);

  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white"
      style={{
        width: size,
        height: size,
        backgroundColor: colorFor(symbol),
        fontSize: size * 0.44,
      }}
      aria-hidden
    >
      {initial}
    </span>
  );
}
