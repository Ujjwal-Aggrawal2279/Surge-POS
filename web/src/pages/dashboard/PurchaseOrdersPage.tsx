import { GenericListPage } from "./GenericListPage";

function fmtCurr(v: unknown) {
  const n = Number(v ?? 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export function PurchaseOrdersPage() {
  return (
    <GenericListPage
      title="Purchase Orders"
      doctype="Purchase Order"
      fields={["name", "supplier", "transaction_date", "status", "grand_total"]}
      searchField="supplier"
      columns={[
        { key: "name", label: "PO #" },
        { key: "supplier", label: "Supplier" },
        { key: "transaction_date", label: "Date" },
        { key: "status", label: "Status", render: (v) => (
          <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${v === "Completed" ? "bg-emerald-50 text-emerald-700" : v === "Cancelled" ? "bg-red-50 text-red-600" : "bg-[#F4F3FF] text-[#6938EF]"}`}>
            {String(v)}
          </span>
        )},
        { key: "grand_total", label: "Total", align: "right", render: fmtCurr },
      ]}
    />
  );
}
