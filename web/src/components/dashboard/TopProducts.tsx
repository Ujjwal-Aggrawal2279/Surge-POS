import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Package, Loader2 } from "lucide-react";
import { get } from "@/lib/api";
import type { TopProduct } from "@/types/pos";

type ProductPeriod = "today" | "week" | "month" | "all";

const PERIODS: { value: ProductPeriod; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "week",  label: "This Week" },
  { value: "month", label: "This Month" },
  { value: "all",   label: "All Time" },
];

const AVATAR_BG = [
  "bg-[#FE9F43]", "bg-[#0E9384]", "bg-[#6938EF]", "bg-[#155EEF]", "bg-[#EF4444]",
] as const;

function avatarBg(code: string): string {
  let h = 0;
  for (let i = 0; i < code.length; i++) h = (h * 31 + code.charCodeAt(i)) >>> 0;
  return AVATAR_BG[h % AVATAR_BG.length] ?? "bg-[#FE9F43]";
}

const fmtINR = new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0,
});

export function TopProducts() {
  const [period, setPeriod] = useState<ProductPeriod>("today");

  const { data: products = [], isLoading } = useQuery<TopProduct[]>({
    queryKey: ["top-products", period],
    queryFn: () => get<TopProduct[]>("surge.api.dashboard.get_top_products", { period }),
    staleTime: 120_000,
    placeholderData: [],
  });

  const totalQty = products.reduce((s, p) => s + p.total_qty, 0);

  return (
    <div className="flex flex-col rounded-lg border border-[#E6EAED] bg-white">

      {/* Header */}
      <div className="flex items-center gap-2 rounded-t-lg border-b border-[#E6EAED] bg-white px-5 py-3.75">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#FFECF4]">
          <Package className="h-4 w-4 text-[#DD2590]" />
        </div>
        <p className="flex-1 text-lg font-bold text-[#212B36]">Top Products</p>

        {/* Filter dropdown — calendar icon + text + chevron */}
        <div className="relative">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as ProductPeriod)}
            title="Filter period"
            className="appearance-none cursor-pointer rounded border border-[#E6EAED] bg-white py-1.5 pl-7 pr-6 text-xs font-semibold text-[#212B36] outline-none"
          >
            {PERIODS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          {/* Calendar icon left */}
          <svg className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-[#212B36]" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1">
            <rect x="1" y="2" width="10" height="9" rx="1"/>
            <line x1="1" y1="5" x2="11" y2="5"/>
            <line x1="4" y1="1" x2="4" y2="3"/>
            <line x1="8" y1="1" x2="8" y2="3"/>
          </svg>
          {/* Chevron right */}
          <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-1.5 w-2 text-[#212B36]" viewBox="0 0 8 4" fill="none">
            <path d="M0 0L4 4L8 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center py-10">
          <Loader2 className="h-5 w-5 animate-spin text-[#DD2590]" />
        </div>
      ) : products.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-[#919EAB]">No data</p>
      ) : (
        <div className="flex flex-col gap-3 p-5">
          {products.map((p, idx) => {
            const avgRate = p.total_qty > 0 ? p.total_amount / p.total_qty : 0;
            const pct     = totalQty > 0 ? Math.round((p.total_qty / totalQty) * 100) : 0;
            const isUp = idx < products.length - 1 || pct > 20;

            return (
              <div key={p.item_code}>
                <div className="flex items-center justify-between gap-4">

                  {/* Avatar + info */}
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <div
                      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-[10px] text-sm font-bold text-white ${avatarBg(p.item_code)}`}
                    >
                      {p.item_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex min-w-0 flex-col gap-1">
                      <p className="truncate text-sm font-bold text-[#212B36]">{p.item_name}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] text-[#646B72]">{fmtINR.format(avgRate)}</span>
                        {/* Orange dot divider */}
                        <span className="h-1 w-1 shrink-0 rounded-full bg-[#E04F16]" />
                        <span className="text-[13px] text-[#646B72]">{p.total_qty.toFixed(0)} sold</span>
                      </div>
                    </div>
                  </div>

                  {/* Outlined trend badge */}
                  <div className={`shrink-0 rounded-[5px] px-1.5 py-1 text-[10px] font-medium ${
                    isUp
                      ? "border border-[#3EB780] text-[#3EB780]"
                      : "border border-[#E70D0D] text-[#E70D0D]"
                  }`}>
                    {isUp ? "↑" : "↓"} {pct}%
                  </div>
                </div>

                {/* Divider — except after last item */}
                {idx < products.length - 1 && (
                  <div className="mt-3 border-t border-[#E6EAED]" />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
