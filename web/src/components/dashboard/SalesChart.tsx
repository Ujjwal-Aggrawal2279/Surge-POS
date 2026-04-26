import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import { Loader2 } from "lucide-react";
import type { ChartData } from "@/types/pos";

type Period = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y";
const PERIODS: Period[] = ["1D", "1W", "1M", "3M", "6M", "1Y"];

const BAR_W = 14;
const GAP = 4;
const PAIR = BAR_W * 2 + GAP + 8; // 8px inter-pair gap
const H = 160;
const LABEL_H = 20;

function fmt(n: number) {
  if (n >= 1_00_000) return `${(n / 1_00_000).toFixed(0)}L`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return `${n.toFixed(0)}`;
}

export function SalesChart() {
  const [period, setPeriod] = useState<Period>("1M");

  const { data, isLoading } = useQuery({
    queryKey: ["chart", period],
    queryFn: () => get<ChartData>("surge.api.dashboard.get_chart_data", { period }),
    staleTime: 120_000,
  });

  const labels = data?.labels ?? [];
  const sales = data?.sales ?? [];
  const purchases = data?.purchases ?? [];
  const maxVal = Math.max(...sales, ...purchases, 1);
  const svgW = Math.max(labels.length * PAIR + 16, 320);

  return (
    <div className="flex flex-1 flex-col rounded-2xl border border-[#E6EAED] bg-white p-5 shadow-sm min-w-0">
      <div className="mb-4 flex items-center justify-between gap-2 flex-wrap">
        <p className="text-sm font-bold text-[#212B36]">Sales Overview</p>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`rounded px-2 py-0.5 text-xs font-semibold transition-colors ${
                period === p
                  ? "bg-[#6938EF] text-white"
                  : "text-[#637381] hover:bg-[#F4F6F8]"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="mb-3 flex items-center gap-4 text-xs text-[#637381]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#6938EF]" />Sales
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#0E9384]" />Purchase
        </span>
      </div>

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center py-10">
          <Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" />
        </div>
      ) : labels.length === 0 ? (
        <p className="py-10 text-center text-sm text-[#919EAB]">No data for this period</p>
      ) : (
        <div className="overflow-x-auto">
          <svg
            width={svgW}
            height={H + LABEL_H}
            viewBox={`0 0 ${svgW} ${H + LABEL_H}`}
            className="min-w-full"
          >
            {/* Y-axis grid lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
              const y = H - frac * H;
              return (
                <g key={frac}>
                  <line x1={0} y1={y} x2={svgW} y2={y} stroke="#F4F6F8" strokeWidth={1} />
                  <text x={2} y={y - 3} fontSize={8} fill="#919EAB">
                    {fmt(frac * maxVal)}
                  </text>
                </g>
              );
            })}

            {labels.map((lbl, i) => {
              const x = 16 + i * PAIR;
              const sH = ((sales[i] ?? 0) / maxVal) * (H - 12);
              const pH = ((purchases[i] ?? 0) / maxVal) * (H - 12);
              return (
                <g key={lbl}>
                  {/* Sales bar */}
                  <rect
                    x={x}
                    y={H - sH}
                    width={BAR_W}
                    height={sH}
                    rx={3}
                    fill="#6938EF"
                    opacity={0.85}
                  />
                  {/* Purchase bar */}
                  <rect
                    x={x + BAR_W + GAP}
                    y={H - pH}
                    width={BAR_W}
                    height={pH}
                    rx={3}
                    fill="#0E9384"
                    opacity={0.85}
                  />
                  {/* Label */}
                  <text
                    x={x + BAR_W}
                    y={H + LABEL_H - 4}
                    fontSize={8}
                    fill="#919EAB"
                    textAnchor="middle"
                  >
                    {lbl}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </div>
  );
}
