import { AlertTriangle, Loader2 } from "lucide-react";
import { useWidgetsData } from "@/hooks/useWidgetsData";
import type { DashboardPage } from "@/types/pos";

const AVATAR_BG = [
  "bg-[#FE9F43]", "bg-[#0E9384]", "bg-[#6938EF]", "bg-[#155EEF]", "bg-[#EF4444]",
] as const;

function avatarBg(code: string): string {
  let h = 0;
  for (let i = 0; i < code.length; i++) h = (h * 31 + code.charCodeAt(i)) >>> 0;
  return AVATAR_BG[h % AVATAR_BG.length] ?? "bg-[#FE9F43]";
}

interface Props {
  onNavigate: (page: DashboardPage) => void;
}

export function LowStock({ onNavigate }: Props) {
  const { data, isLoading } = useWidgetsData();
  const items = data?.low_stock ?? [];

  return (
    <div className="flex flex-col rounded-lg border border-[#E6EAED] bg-white">

      {/* Header */}
      <div className="flex items-center gap-2 rounded-t-lg border-b border-[#E6EAED] bg-white px-5 py-3.75">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#FFEDE9]">
          <AlertTriangle className="h-4 w-4 text-[#FF0000]" />
        </div>
        <p className="flex-1 text-lg font-bold text-[#212B36]">Low Stock Products</p>
        <button
          type="button"
          onClick={() => onNavigate("stock")}
          className="shrink-0 text-[13px] font-medium text-[#212B36] underline"
        >
          View All
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center py-10">
          <Loader2 className="h-5 w-5 animate-spin text-[#FF0000]" />
        </div>
      ) : items.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-[#919EAB]">All stock levels OK</p>
      ) : (
        <div className="flex flex-col gap-6 p-5">
          {items.map((item) => (
            <div key={`${item.item_code}:${item.warehouse}`} className="flex items-center justify-between gap-4">

              {/* Avatar + details */}
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-[10px] text-sm font-bold text-white ${avatarBg(item.item_code)}`}>
                  {item.item_name.charAt(0).toUpperCase()}
                </div>
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="truncate text-sm font-bold text-[#212B36]">{item.item_name}</p>
                  <p className="text-[13px] text-[#646B72]">ID : #{item.item_code}</p>
                </div>
              </div>

              {/* Stock info — right aligned */}
              <div className="flex shrink-0 flex-col items-end gap-1">
                <span className="text-[13px] text-[#646B72]">Instock</span>
                <span className="text-sm font-medium text-[#E04F16]">
                  {String(item.actual_qty.toFixed(0)).padStart(2, "0")}
                </span>
              </div>

            </div>
          ))}
        </div>
      )}
    </div>
  );
}
