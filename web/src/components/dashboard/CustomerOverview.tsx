import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { get } from "@/lib/api";
import type { CustomerOverviewData } from "@/types/pos";

type Period = "today" | "this_week" | "last_week" | "this_month" | "last_month";

const PERIODS: { value: Period; label: string }[] = [
  { value: "today",      label: "Today" },
  { value: "this_week",  label: "This Week" },
  { value: "last_week",  label: "Last Week" },
  { value: "this_month", label: "This Month" },
  { value: "last_month", label: "Last Month" },
];

// Two concentric donut rings
const CX = 54;
const CY = 54;
const OUTER_R  = 44;   // outer ring radius
const INNER_R  = 28;   // inner ring radius
const RING_SW  = 11;   // stroke width for both rings
const OUTER_C  = 2 * Math.PI * OUTER_R;
const INNER_C  = 2 * Math.PI * INNER_R;

const EMPTY_DATA: CustomerOverviewData = {
  first_time: 0, returning: 0, first_time_pct: 0, returning_pct: 0, total: 0,
};

export function CustomerOverview() {
  const [period, setPeriod] = useState<Period>("today");

  const { data, isLoading } = useQuery<CustomerOverviewData>({
    queryKey: ["customer-overview", period],
    queryFn: () => get<CustomerOverviewData>("surge.api.dashboard.get_customer_overview", { period }),
    staleTime: 60_000,
    placeholderData: EMPTY_DATA,
  });

  const total  = data?.total ?? 0;

  // Arc lengths — rotate both to start at 12 o'clock (offset = circumference/4)
  const ftArc  = total > 0 ? (data!.first_time / total) * OUTER_C : 0;
  const retArc = total > 0 ? (data!.returning  / total) * INNER_C : 0;

  return (
    <div className="flex flex-col gap-4 p-5">

      {/* Header */}
      <div className="flex items-center gap-4">
        <p className="flex-1 text-sm font-bold text-[#212B36]">Customer Overview</p>
        <div className="relative">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
            title="Filter period"
            className="appearance-none cursor-pointer rounded border border-[#E04F16] bg-white py-1 pl-2.5 pr-6 text-[11px] font-semibold text-[#E04F16] outline-none"
          >
            {PERIODS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <svg className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 h-2 w-2.5" viewBox="0 0 10 6" fill="none">
            <path d="M1 1L5 5L9 1" stroke="#E04F16" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-[#E04F16]" />
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">

          {/* Double concentric donut */}
          <svg width={108} height={108} viewBox="0 0 108 108" className="shrink-0">
            {/* Outer ring background */}
            <circle cx={CX} cy={CY} r={OUTER_R} fill="none" stroke="#F4F6F8" strokeWidth={RING_SW} />
            {/* Outer ring — first-time (orange-red) */}
            <circle
              cx={CX} cy={CY} r={OUTER_R}
              fill="none" stroke="#E04F16" strokeWidth={RING_SW}
              strokeDasharray={`${ftArc} ${OUTER_C - ftArc}`}
              strokeDashoffset={OUTER_C / 4}
              strokeLinecap="round"
            />

            {/* Inner ring background */}
            <circle cx={CX} cy={CY} r={INNER_R} fill="none" stroke="#F4F6F8" strokeWidth={RING_SW} />
            {/* Inner ring — returning (teal) */}
            <circle
              cx={CX} cy={CY} r={INNER_R}
              fill="none" stroke="#0E9384" strokeWidth={RING_SW}
              strokeDasharray={`${retArc} ${INNER_C - retArc}`}
              strokeDashoffset={INNER_C / 4}
              strokeLinecap="round"
            />

            {/* Center label */}
            <text x={CX} y={CY - 5} textAnchor="middle" fontSize={15} fontWeight={700} fill="#212B36">{total}</text>
            <text x={CX} y={CY + 9} textAnchor="middle" fontSize={9} fill="#919EAB">total</text>
          </svg>

          {/* Stats — two columns with vertical divider */}
          <div className="flex w-full items-center divide-x divide-[#E6EAED]">

            <div className="flex flex-1 flex-col items-center gap-2 pr-2">
              <span className="text-xl font-bold text-[#212B36]">{data?.first_time ?? 0}</span>
              <span className="text-xs text-[#E04F16]">First Time</span>
              <span className="inline-flex items-center rounded-[5px] bg-[#3EB780] px-1.5 py-0.5 text-[10px] font-medium text-white">
                ↑ {data?.first_time_pct ?? 0}%
              </span>
            </div>

            <div className="flex flex-1 flex-col items-center gap-2 pl-2">
              <span className="text-xl font-bold text-[#212B36]">{data?.returning ?? 0}</span>
              <span className="text-xs text-[#0E9384]">Returning</span>
              <span className="inline-flex items-center rounded-[5px] bg-[#3EB780] px-1.5 py-0.5 text-[10px] font-medium text-white">
                ↑ {data?.returning_pct ?? 0}%
              </span>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
