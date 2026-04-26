import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import { Loader2, Search } from "lucide-react";

interface ItemRow {
  name: string;
  item_name: string;
  item_group: string;
  stock_uom: string;
  disabled: 0 | 1;
}

interface Props {
  disabled?: boolean;
}

export function ProductsPage({ disabled = false }: Props) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const PAGE = 20;

  const filters: [string, string, string, unknown][] = [
    ["Item", "disabled", "=", disabled ? 1 : 0],
  ];
  if (search) filters.push(["Item", "item_name", "like", `%${search}%`]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["mgr-items", disabled, search, page],
    queryFn: () =>
      get<{ data: ItemRow[] }>("surge.api.dashboard.manager_get_list", {
        doctype: "Item",
        fields: JSON.stringify(["name", "item_name", "item_group", "stock_uom", "disabled"]),
        filters: JSON.stringify(filters),
        order_by: "modified desc",
        limit_start: page * PAGE,
        limit_page_length: PAGE,
      }),
    staleTime: 30_000,
  });

  const rows = data?.data ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-[#212B36]">{disabled ? "Disabled Products" : "Products"}</h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#919EAB]" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search items…"
            className="rounded-lg border border-[#E6EAED] py-2 pl-8 pr-3 text-sm outline-none focus:border-[#6938EF]"
          />
        </div>
      </div>

      <div className="rounded-2xl border border-[#E6EAED] bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>
        ) : error ? (
          <p className="py-12 text-center text-sm text-red-500">{(error as Error).message}</p>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-sm text-[#919EAB]">No items found</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[#E6EAED] bg-[#F8FAFB]">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-[#919EAB]">Item Code</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">Name</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">Group</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">UOM</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F4F6F8]">
              {rows.map((r) => (
                <tr key={r.name} className="hover:bg-[#F8FAFB]">
                  <td className="px-5 py-3 font-mono text-xs text-[#637381]">{r.name}</td>
                  <td className="px-3 py-3 font-semibold text-[#212B36]">{r.item_name}</td>
                  <td className="px-3 py-3 text-[#637381]">{r.item_group}</td>
                  <td className="px-3 py-3 text-[#637381]">{r.stock_uom}</td>
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
