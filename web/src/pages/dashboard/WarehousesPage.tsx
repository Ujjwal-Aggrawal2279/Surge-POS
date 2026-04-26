import { GenericListPage } from "./GenericListPage";

export function WarehousesPage() {
  return (
    <GenericListPage
      title="Warehouses"
      doctype="Warehouse"
      fields={["name", "warehouse_type", "company", "is_group", "disabled"]}
      searchField="name"
      columns={[
        { key: "name", label: "Warehouse" },
        { key: "warehouse_type", label: "Type" },
        { key: "company", label: "Company" },
        { key: "is_group", label: "Group", render: (v) => (
          <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${v ? "bg-[#F4F3FF] text-[#6938EF]" : "bg-[#F4F6F8] text-[#637381]"}`}>
            {v ? "Yes" : "No"}
          </span>
        )},
      ]}
    />
  );
}
