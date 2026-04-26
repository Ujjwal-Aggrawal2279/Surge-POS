import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface GroupRow { name: string; parent_item_group: string; is_group: 0 | 1 }

export function CategoryPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["mgr-item-groups"],
    queryFn: () =>
      get<{ data: GroupRow[] }>("surge.api.dashboard.manager_get_list", {
        doctype: "Item Group",
        fields: JSON.stringify(["name", "parent_item_group", "is_group"]),
        filters: JSON.stringify([]),
        order_by: "name asc",
        limit_page_length: 100,
      }),
    staleTime: 60_000,
  });
  const rows = data?.data ?? [];

  return (
    <div>
      <h2 className="mb-4 text-lg font-bold text-[#212B36]">Category</h2>
      <div className="rounded-2xl border border-[#E6EAED] bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>
        ) : error ? (
          <p className="py-12 text-center text-sm text-red-500">{(error as Error).message}</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[#E6EAED] bg-[#F8FAFB]">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-[#919EAB]">Name</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">Parent</th>
                <th className="px-3 py-3 text-left text-xs font-semibold text-[#919EAB]">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F4F6F8]">
              {rows.map((r) => (
                <tr key={r.name} className="hover:bg-[#F8FAFB]">
                  <td className="px-5 py-3 font-semibold text-[#212B36]">{r.name}</td>
                  <td className="px-3 py-3 text-[#637381]">{r.parent_item_group || "—"}</td>
                  <td className="px-3 py-3">
                    <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${r.is_group ? "bg-[#F4F3FF] text-[#6938EF]" : "bg-[#F4F6F8] text-[#637381]"}`}>
                      {r.is_group ? "Group" : "Leaf"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
