import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { get } from "@/lib/api";
import type { OverallInfoData } from "@/types/pos";
import customersIcon from "@/assets/icons/overall-customers.png";
import suppliersIcon from "@/assets/icons/overall-suppliers.png";
import ordersIcon    from "@/assets/icons/overall-orders.png";

export function OverallInfo() {
  const { data, isLoading } = useQuery<OverallInfoData>({
    queryKey: ["overall-info"],
    queryFn: () => get<OverallInfoData>("surge.api.dashboard.get_overall_info"),
    staleTime: 300_000,
    placeholderData: { customers: 0, suppliers: 0, orders: 0 },
  });

  const items = [
    { label: "Suppliers", value: data?.suppliers ?? 0, icon: suppliersIcon },
    { label: "Customers", value: data?.customers ?? 0, icon: customersIcon },
    { label: "Orders",    value: data?.orders    ?? 0, icon: ordersIcon    },
  ];

  return (
    <div className="flex flex-col gap-6 border-b border-[#E6EAED] bg-white p-5">
      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-[#6938EF]" />
        </div>
      ) : (
        <div className="flex gap-4">
          {items.map(({ label, value, icon }) => (
            <div
              key={label}
              className="flex flex-1 flex-col items-center gap-2.5 rounded-lg border border-[#E6EAED] bg-[#F9FAFB] px-2 py-3"
            >
              <img src={icon} alt={label} className="h-6 w-6 object-contain" />
              <div className="flex flex-col items-center gap-0.5">
                <span className="text-xs font-normal text-[#646B72]">{label}</span>
                <span className="text-base font-bold text-[#212B36]">{value.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
