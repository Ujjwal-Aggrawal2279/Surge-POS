import { GenericListPage } from "./GenericListPage";

function fmtCurr(v: unknown) {
  const n = Number(v ?? 0);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export function SalesInvoicesPage() {
  return (
    <GenericListPage
      title="Sales Invoices"
      doctype="Sales Invoice"
      fields={["name", "customer", "posting_date", "status", "grand_total", "is_return"]}
      searchField="customer"
      extraFilters={[["Sales Invoice", "docstatus", "=", 1]]}
      columns={[
        { key: "name", label: "Invoice #" },
        { key: "customer", label: "Customer" },
        { key: "posting_date", label: "Date" },
        { key: "status", label: "Status", render: (v, row) => (
          <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${row.is_return ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-700"}`}>
            {row.is_return ? "Return" : String(v)}
          </span>
        )},
        { key: "grand_total", label: "Total", align: "right", render: fmtCurr },
      ]}
    />
  );
}
