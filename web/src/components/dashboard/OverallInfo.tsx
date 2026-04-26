import { Users, Truck, MonitorCheck } from "lucide-react";
import type { OverviewData } from "@/types/pos";

interface Props {
  overview: OverviewData;
}

export function OverallInfo({ overview }: Props) {
  const items = [
    { label: "Customers", value: overview.customers, icon: Users, color: "text-[#6938EF]", bg: "bg-[#F4F3FF]" },
    { label: "Suppliers", value: overview.suppliers, icon: Truck, color: "text-[#0E9384]", bg: "bg-[#E6FBF8]" },
    { label: "POS Sessions", value: overview.pos_sessions, icon: MonitorCheck, color: "text-[#F79009]", bg: "bg-[#FEF3C7]" },
  ];
  return (
    <div className="flex w-72 shrink-0 flex-col gap-4 rounded-2xl border border-[#E6EAED] bg-white p-5 shadow-sm">
      <p className="text-sm font-bold text-[#212B36]">Overall</p>
      <div className="flex flex-col gap-3">
        {items.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="flex items-center gap-3">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${bg}`}>
              <Icon className={`h-5 w-5 ${color}`} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs text-[#919EAB]">{label}</p>
              <p className="text-base font-black text-[#212B36]">{value.toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
