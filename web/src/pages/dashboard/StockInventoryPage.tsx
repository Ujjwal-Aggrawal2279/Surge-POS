import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import { Loader2, Search } from "lucide-react";

interface BinRow {
  item_code: string;
  item_name: string;
  warehouse: string;
  actual_qty: number;
  reserved_qty: number;
  ordered_qty: number;
}

export function StockInventoryPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const PAGE = 25;

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["stock-inventory", search, page],
    queryFn: () =>
      get<BinRow[]>("surge.api.dashboard.get_stock_inventory", {
        search,
        page,
        page_size: PAGE,
      }),
    staleTime: 30_000,
  });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-[#212B36]">Stock Inventory</h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#919EAB]" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search item…"
            className="rounded-lg border border-[#E6EAED] py-2 pl-8 pr-3 text-sm outline-none focus:border-[#6938EF]"
          />
        </div>
      </div>
      <div className="rounded-2xl border border-[#E6EAED] bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-sm text-[#919EAB]">No stock data</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[#E6EAED] bg-[#F8FAFB]">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-[#919EAB]">Item</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">Warehouse</th>
                <th className="px-3 py-3 text-right text-xs font-semibold text-[#919EAB]">Actual</th>
                <th className="px-3 py-3 text-right text-xs font-semibold text-[#919EAB]">Reserved</th>
                <th className="px-3 py-3 text-right text-xs font-semibold text-[#919EAB]">Ordered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F4F6F8]">
              {rows.map((r, i) => (
                <tr key={i} className="hover:bg-[#F8FAFB]">
                  <td className="px-5 py-3">
                    <p className="font-semibold text-[#212B36]">{r.item_name || r.item_code}</p>
                    <p className="text-[11px] text-[#919EAB]">{r.item_code}</p>
                  </td>
                  <td className="px-3 py-3 text-xs text-[#637381]">{r.warehouse}</td>
                  <td className={`px-3 py-3 text-right font-bold ${r.actual_qty <= 0 ? "text-red-500" : "text-[#212B36]"}`}>
                    {r.actual_qty}
                  </td>
                  <td className="px-3 py-3 text-right text-[#637381]">{r.reserved_qty}</td>
                  <td className="px-3 py-3 text-right text-[#0E9384]">{r.ordered_qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="mt-4 flex items-center justify-between text-xs text-[#919EAB]">
        <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)}
          className="rounded border border-[#E6EAED] px-3 py-1.5 disabled:opacity-40 hover:bg-[#F4F6F8]">← Prev</button>
        <span>Page {page + 1}</span>
        <button type="button" disabled={rows.length < PAGE} onClick={() => setPage((p) => p + 1)}
          className="rounded border border-[#E6EAED] px-3 py-1.5 disabled:opacity-40 hover:bg-[#F4F6F8]">Next →</button>
      </div>
    </div>
  );
}
