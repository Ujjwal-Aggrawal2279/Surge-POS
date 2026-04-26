import { cn } from "@/lib/utils";

interface Props {
  title: string;
  amount: number;
  imgSrc: string;
  iconBg: string;
  trendPct?: number;
  currency?: string;
}

function fmt(n: number, currency = "₹") {
  if (n >= 1_00_00_000) return `${currency}${(n / 1_00_00_000).toFixed(1)}Cr`;
  if (n >= 1_00_000)    return `${currency}${(n / 1_00_000).toFixed(1)}L`;
  if (n >= 1_000)       return `${currency}${(n / 1_000).toFixed(1)}K`;
  return `${currency}${n.toFixed(0)}`;
}

export function StatCard({ title, amount, imgSrc, iconBg, trendPct, currency }: Props) {
  const up = (trendPct ?? 0) >= 0;
  return (
    <div className="flex flex-1 flex-col gap-3 rounded-lg bg-white p-4 min-w-45 shadow-[0_4px_24px_rgba(236,236,236,0.25)]">
      <div className="flex items-center justify-between">
        <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", iconBg)}>
          <img src={imgSrc} alt={title} className="h-5 w-5 object-contain" />
        </div>
        <span className="cursor-pointer text-[13px] font-medium text-[#212b36]">View All</span>
      </div>
      <div>
        <p className="text-lg font-bold text-[#212b36]">{fmt(amount, currency)}</p>
        <p className="text-sm font-normal text-[#7a8086]">{title}</p>
      </div>
      {trendPct !== undefined && (
        <p className="text-[13px] font-medium text-[#646b72]">
          <span className={up ? "text-[#3eb780]" : "text-[#ef4444]"}>
            {up ? "+" : ""}{trendPct}%
          </span>
          {" "}vs Last Month
        </p>
      )}
    </div>
  );
}
