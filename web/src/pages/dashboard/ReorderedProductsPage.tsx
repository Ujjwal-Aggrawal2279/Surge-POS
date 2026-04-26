import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import { Loader2, RefreshCcw } from "lucide-react";

interface ReorderRow {
  parent: string;
  warehouse: string;
  warehouse_reorder_level: number;
  warehouse_reorder_qty: number;
}

export function ReorderedProductsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["mgr-reorder-items"],
    queryFn: () =>
      get<{ data: ReorderRow[] }>("surge.api.dashboard.manager_get_list", {
        doctype: "Item Reorder",
        fields: JSON.stringify(["parent", "warehouse", "warehouse_reorder_level", "warehouse_reorder_qty"]),
        filters: JSON.stringify([]),
        order_by: "warehouse_reorder_level desc",
        limit_page_length: 50,
      }),
    staleTime: 60_000,
  });

  const rows = data?.data ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <RefreshCcw className="h-5 w-5 text-[#6938EF]" />
        <h2 className="text-lg font-bold text-[#212B36]">Reorder Points</h2>
      </div>
      <div className="rounded-2xl border border-[#E6EAED] bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>
        ) : error ? (
          <p className="py-12 text-center text-sm text-red-500">{(error as Error).message}</p>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-sm text-[#919EAB]">No reorder points configured</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[#E6EAED] bg-[#F8FAFB]">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-[#919EAB]">Item Code</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">Warehouse</th>
                <th className="px-3 py-3 text-right text-xs font-semibold text-[#919EAB]">Reorder Level</th>
                <th className="px-3 py-3 text-right text-xs font-semibold text-[#919EAB]">Reorder Qty</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F4F6F8]">
              {rows.map((r, i) => (
                <tr key={i} className="hover:bg-[#F8FAFB]">
                  <td className="px-5 py-3 font-semibold text-[#212B36]">{r.parent}</td>
                  <td className="px-3 py-3 text-[#637381]">{r.warehouse}</td>
                  <td className="px-3 py-3 text-right font-mono text-[#637381]">{r.warehouse_reorder_level}</td>
                  <td className="px-3 py-3 text-right font-mono text-[#6938EF] font-semibold">{r.warehouse_reorder_qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
