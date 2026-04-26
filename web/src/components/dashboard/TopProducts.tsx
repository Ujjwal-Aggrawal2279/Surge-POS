import type { TopProduct } from "@/types/pos";

interface Props {
  products: TopProduct[];
}

export function TopProducts({ products }: Props) {
  const maxQty = Math.max(...products.map((p) => p.total_qty), 1);
  return (
    <div className="flex w-72 shrink-0 flex-col rounded-2xl border border-[#E6EAED] bg-white shadow-sm">
      <div className="border-b border-[#E6EAED] px-5 py-4">
        <p className="text-sm font-bold text-[#212B36]">Top Products</p>
      </div>
      {products.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-[#919EAB]">No data</p>
      ) : (
        <ul className="divide-y divide-[#F4F6F8]">
          {products.map((p, i) => (
            <li key={p.item_code} className="flex items-center gap-3 px-5 py-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#F4F3FF] text-[11px] font-bold text-[#6938EF]">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-[#212B36]">{p.item_name}</p>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[#F4F6F8]">
                  <div
                    className="h-full rounded-full bg-[#6938EF]"
                    style={{ width: `${(p.total_qty / maxQty) * 100}%` }}
                  />
                </div>
              </div>
              <span className="shrink-0 text-xs font-bold text-[#6938EF]">{p.total_qty.toFixed(0)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
