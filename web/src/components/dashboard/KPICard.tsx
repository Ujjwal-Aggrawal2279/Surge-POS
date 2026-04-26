
interface Props {
  title: string;
  amount: number;
  bg: string;
  imgSrc: string;
  trendPct?: number;
  currency?: string;
}

function fmt(n: number, currency = "₹") {
  if (n >= 1_00_00_000) return `${currency}${(n / 1_00_00_000).toFixed(1)}Cr`;
  if (n >= 1_00_000)    return `${currency}${(n / 1_00_000).toFixed(1)}L`;
  if (n >= 1_000)       return `${currency}${(n / 1_000).toFixed(1)}K`;
  return `${currency}${n.toFixed(0)}`;
}

export function KPICard({ title, amount, bg, imgSrc, trendPct, currency }: Props) {
  const up = (trendPct ?? 0) >= 0;
  return (
    <div className="flex flex-1 flex-col gap-3 rounded-lg p-4" style={{ background: bg }}>
      {/* Row 1: solid white icon box + title */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white shadow-[0_2px_8px_rgba(0,0,0,0.18)]">
          <img src={imgSrc} alt={title} className="h-6 w-6 object-contain" />
        </div>
        <p className="text-sm font-medium text-white">{title}</p>
      </div>
      {/* Row 2: amount + trend badge */}
      <div className="flex items-end justify-between gap-2">
        <p className="text-xl font-bold text-white">{fmt(amount, currency)}</p>
        {trendPct !== undefined && (
          <span className="flex items-center gap-0.5 rounded-full border border-white/30 bg-white/20 px-2.5 py-0.5 text-xs font-semibold text-white">
            {up ? "▲" : "▼"} {up ? "+" : ""}{trendPct}%
          </span>
        )}
      </div>
    </div>
  );
}
