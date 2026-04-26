import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import { Loader2, Search } from "lucide-react";

export interface ColDef {
  key: string;
  label: string;
  align?: "left" | "right";
  render?: (val: unknown, row: Record<string, unknown>) => React.ReactNode;
}

interface Props {
  title: string;
  doctype: string;
  fields: string[];
  columns: ColDef[];
  orderBy?: string;
  searchField?: string;
  pageSize?: number;
  extraFilters?: [string, string, string, unknown][];
}

export function GenericListPage({
  title, doctype, fields, columns, orderBy, searchField, pageSize = 20, extraFilters = [],
}: Props) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const PAGE = pageSize;

  const filters: [string, string, string, unknown][] = [...extraFilters];
  if (search && searchField) filters.push([doctype, searchField, "like", `%${search}%`]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["mgr-list", doctype, search, page, JSON.stringify(extraFilters)],
    queryFn: () =>
      get<{ data: Record<string, unknown>[] }>("surge.api.dashboard.manager_get_list", {
        doctype,
        fields: JSON.stringify(fields),
        filters: JSON.stringify(filters),
        order_by: orderBy ?? "modified desc",
        limit_start: page * PAGE,
        limit_page_length: PAGE,
      }),
    staleTime: 30_000,
  });

  const rows = data?.data ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-[#212B36]">{title}</h2>
        {searchField && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#919EAB]" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              placeholder="Search…"
              className="rounded-lg border border-[#E6EAED] py-2 pl-8 pr-3 text-sm outline-none focus:border-[#6938EF]"
            />
          </div>
        )}
      </div>
      <div className="rounded-2xl border border-[#E6EAED] bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>
        ) : error ? (
          <p className="py-12 text-center text-sm text-red-500">{(error as Error).message}</p>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-sm text-[#919EAB]">No records found</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[#E6EAED] bg-[#F8FAFB]">
              <tr>
                {columns.map((c) => (
                  <th key={c.key} className={`px-5 py-3 text-xs font-semibold text-[#919EAB] ${c.align === "right" ? "text-right" : "text-left"}`}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F4F6F8]">
              {rows.map((row, i) => (
                <tr key={i} className="hover:bg-[#F8FAFB]">
                  {columns.map((c) => (
                    <td key={c.key} className={`px-5 py-3 ${c.align === "right" ? "text-right" : ""} text-[#212B36]`}>
                      {c.render ? c.render(row[c.key], row) : String(row[c.key] ?? "—")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {(rows.length === PAGE || page > 0) && (
        <div className="mt-4 flex items-center justify-between text-xs text-[#919EAB]">
          <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)}
            className="rounded border border-[#E6EAED] px-3 py-1.5 disabled:opacity-40 hover:bg-[#F4F6F8]">← Prev</button>
          <span>Page {page + 1}</span>
          <button type="button" disabled={rows.length < PAGE} onClick={() => setPage((p) => p + 1)}
            className="rounded border border-[#E6EAED] px-3 py-1.5 disabled:opacity-40 hover:bg-[#F4F6F8]">Next →</button>
        </div>
      )}
    </div>
  );
}
