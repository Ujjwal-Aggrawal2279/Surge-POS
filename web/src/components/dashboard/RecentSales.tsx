import { CornerDownLeft } from "lucide-react";
import type { RecentTransaction } from "@/types/pos";

interface Props {
  transactions: RecentTransaction[];
}

function fmt(n: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export function RecentSales({ transactions }: Props) {
  return (
    <div className="flex flex-1 flex-col rounded-2xl border border-[#E6EAED] bg-white shadow-sm min-w-0">
      <div className="border-b border-[#E6EAED] px-5 py-4">
        <p className="text-sm font-bold text-[#212B36]">Recent Transactions</p>
      </div>
      {transactions.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-[#919EAB]">No transactions</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#F4F6F8]">
                <th className="px-5 py-2.5 text-left font-semibold text-[#919EAB]">Invoice</th>
                <th className="px-3 py-2.5 text-left font-semibold text-[#919EAB]">Customer</th>
                <th className="px-3 py-2.5 text-left font-semibold text-[#919EAB]">Date</th>
                <th className="px-5 py-2.5 text-right font-semibold text-[#919EAB]">Amount</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.name} className="border-b border-[#F8FAFB] hover:bg-[#F8FAFB]">
                  <td className="px-5 py-2.5 font-medium text-[#212B36]">
                    <span className="flex items-center gap-1">
                      {t.is_return && <CornerDownLeft className="h-3 w-3 text-red-400" />}
                      {t.name}
                    </span>
                  </td>
                  <td className="max-w-32 truncate px-3 py-2.5 text-[#637381]">{t.customer}</td>
                  <td className="px-3 py-2.5 text-[#637381]">{t.posting_date}</td>
                  <td className={`px-5 py-2.5 text-right font-semibold ${t.is_return ? "text-red-500" : "text-[#212B36]"}`}>
                    {t.is_return ? "-" : ""}{fmt(t.grand_total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
