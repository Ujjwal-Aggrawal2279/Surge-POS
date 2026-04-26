import { GenericListPage } from "./GenericListPage";

export function POSProfilesPage() {
  return (
    <GenericListPage
      title="POS Profiles"
      doctype="POS Profile"
      fields={["name", "company", "warehouse", "currency", "disabled"]}
      searchField="name"
      columns={[
        { key: "name", label: "Profile" },
        { key: "company", label: "Company" },
        { key: "warehouse", label: "Warehouse" },
        { key: "currency", label: "Currency" },
        { key: "disabled", label: "Status", render: (v) => (
          <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${v ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-700"}`}>
            {v ? "Disabled" : "Active"}
          </span>
        )},
      ]}
    />
  );
}
