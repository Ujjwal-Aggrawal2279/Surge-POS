import { GenericListPage } from "./GenericListPage";

function fmtCurr(v: unknown) {
  const n = Number(v ?? 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export function PurchaseReceiptsPage() {
  return (
    <GenericListPage
      title="Purchase Receipts"
      doctype="Purchase Receipt"
      fields={["name", "supplier", "posting_date", "status", "grand_total", "is_return"]}
      searchField="supplier"
      columns={[
        { key: "name", label: "GRN #" },
        { key: "supplier", label: "Supplier" },
        { key: "posting_date", label: "Date" },
        { key: "status", label: "Status", render: (v) => (
          <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${v === "Completed" ? "bg-emerald-50 text-emerald-700" : "bg-[#F4F6F8] text-[#637381]"}`}>
            {String(v)}
          </span>
        )},
        { key: "grand_total", label: "Total", align: "right", render: fmtCurr },
      ]}
    />
  );
}
