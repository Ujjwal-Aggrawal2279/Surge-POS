import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShoppingCart, Loader2 } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { get } from "@/lib/api";
import type { ChartData } from "@/types/pos";

type Period = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y";
const PERIODS: Period[] = ["1D", "1W", "1M", "3M", "6M", "1Y"];

function fmt(n: number): string {
  if (n >= 1_00_000) return `${(n / 1_00_000).toFixed(1)}L`;
  if (n >= 1_000)    return `${(n / 1_000).toFixed(0)}K`;
  return `${n.toFixed(0)}`;
}

export function SalesChart() {
  const [period, setPeriod] = useState<Period>("1M");

  const { data, isLoading } = useQuery<ChartData>({
    queryKey: ["chart", period],
    queryFn: () => get<ChartData>("surge.api.dashboard.get_chart_data", { period }),
    staleTime: 120_000,
  });

  const labels    = data?.labels    ?? [];
  const sales     = data?.sales     ?? [];
  const purchases = data?.purchases ?? [];

  const chartData = labels.map((label, i) => ({
    label,
    sales:    sales[i]     ?? 0,
    purchase: purchases[i] ?? 0,
  }));

  const totalSales    = sales.reduce((a, b) => a + b, 0);
  const totalPurchase = purchases.reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-1 flex-col rounded-lg border border-[#E6EAED] bg-white shadow-sm min-w-0">

      {/* Header */}
      <div className="flex items-center gap-2 border-b border-[#E6EAED] px-5 py-3.75 rounded-t-lg">
        <div className="flex h-7.5 w-7.5 shrink-0 items-center justify-center rounded-lg bg-[#FFF6EE]">
          <ShoppingCart className="h-3.5 w-3.5 text-[#FE9F43]" />
        </div>
        <p className="flex-1 text-lg font-bold text-[#212B36]">Sales &amp; Purchase</p>
        <div className="flex overflow-hidden rounded bg-[#F9FAFB]">
          {PERIODS.map((p, idx) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`flex h-7.5 w-10.5 items-center justify-center text-xs font-medium transition-colors ${
                idx < PERIODS.length - 1 ? "border-r border-[#E6EAED]" : ""
              } ${period === p ? "bg-[#E04F16] text-white" : "text-[#212B36]"}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col rounded-b-lg p-5">

        {/* Legend */}
        <div className="mb-5 flex gap-2">
          <div className="flex flex-col gap-1 rounded-lg border border-[#E6EAED] p-2">
            <div className="flex items-center gap-1.5">
              <span className="h-1.75 w-1.75 shrink-0 rounded-full bg-[#FFE3CB]" />
              <span className="text-sm text-[#646B72]">Total Purchase</span>
            </div>
            <span className="text-lg font-bold text-[#212B36]">{fmt(totalPurchase)}</span>
          </div>
          <div className="flex flex-col gap-1 rounded-lg border border-[#E6EAED] p-2">
            <div className="flex items-center gap-1.5">
              <span className="h-1.75 w-1.75 shrink-0 rounded-full bg-[#FE9F43]" />
              <span className="text-sm text-[#646B72]">Total Sales</span>
            </div>
            <span className="text-lg font-bold text-[#212B36]">{fmt(totalSales)}</span>
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-1 items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-[#E04F16]" />
          </div>
        ) : labels.length === 0 ? (
          <p className="py-10 text-center text-sm text-[#919EAB]">No data for this period</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={chartData}
              margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
              barCategoryGap="30%"
              barGap={0}
            >
              <CartesianGrid vertical={false} stroke="#F4F6F8" strokeWidth={1} />
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fontWeight: 500, fill: "#646B72" }}
                dy={8}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fontWeight: 500, fill: "#646B72" }}
                tickFormatter={fmt}
                width={44}
              />
              <Tooltip
                formatter={(value, name) => [fmt(Number(value)), name === "purchase" ? "Purchase" : "Sales"]}
                contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E6EAED" }}
                cursor={{ fill: "rgba(0,0,0,0.03)" }}
              />
              {/* Purchase bar behind — peach */}
              <Bar dataKey="purchase" fill="#FFE3CB" radius={[8, 8, 0, 0]} />
              {/* Sales bar in front — orange */}
              <Bar dataKey="sales" fill="#FE9F43" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
