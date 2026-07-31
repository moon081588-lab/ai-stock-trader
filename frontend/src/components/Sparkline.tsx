interface Props {
  values: number[];
  stroke: string;
  width?: number;
  height?: number;
  /** Draw the flat dashed baseline at the first value, like the reference UI. */
  baseline?: boolean;
}

/** Dependency-free SVG sparkline. Recharts would be overkill for 40 points. */
export default function Sparkline({
  values,
  stroke,
  width = 96,
  height = 44,
  baseline = true,
}: Props) {
  if (values.length < 2) {
    return <div style={{ width, height }} className="rounded bg-raised/40" />;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = width / (values.length - 1);

  const y = (v: number) => height - ((v - min) / span) * (height - 4) - 2;
  const path = values.map((v, i) => `${i === 0 ? "M" : "L"}${i * stepX},${y(v)}`).join(" ");
  const area = `${path} L${width},${height} L0,${height} Z`;
  const gradientId = `spark-${stroke.replace("#", "")}`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      {baseline && (
        <line
          x1="0"
          x2={width}
          y1={y(values[0])}
          y2={y(values[0])}
          stroke="#3A3D47"
          strokeWidth="1"
          strokeDasharray="3 3"
        />
      )}
      <path d={area} fill={`url(#${gradientId})`} />
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth="1.6"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
