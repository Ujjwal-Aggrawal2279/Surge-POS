import { AlertTriangle } from "lucide-react";
import type { LowStockItem } from "@/types/pos";

interface Props {
  items: LowStockItem[];
}

export function LowStock({ items }: Props) {
  return (
    <div className="flex w-72 shrink-0 flex-col rounded-2xl border border-[#E6EAED] bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-[#E6EAED] px-5 py-4">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <p className="text-sm font-bold text-[#212B36]">Low Stock</p>
        {items.length > 0 && (
          <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 text-[11px] font-bold text-amber-700">
            {items.length}
          </span>
        )}
      </div>
      {items.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-[#919EAB]">All stock levels OK</p>
      ) : (
        <ul className="max-h-64 divide-y divide-[#F4F6F8] overflow-y-auto">
          {items.map((item) => (
            <li key={`${item.item_code}:${item.warehouse}`} className="px-5 py-3">
              <p className="truncate text-xs font-semibold text-[#212B36]">{item.item_name}</p>
              <p className="text-[11px] text-[#919EAB]">{item.warehouse}</p>
              <div className="mt-1 flex items-center gap-2 text-[11px]">
                <span className="font-bold text-red-500">{item.actual_qty} units</span>
                <span className="text-[#919EAB]">/ reorder at {item.reorder_level}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
