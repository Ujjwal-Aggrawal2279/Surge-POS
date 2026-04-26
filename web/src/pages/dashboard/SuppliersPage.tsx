import { GenericListPage } from "./GenericListPage";

export function SuppliersPage() {
  return (
    <GenericListPage
      title="Suppliers"
      doctype="Supplier"
      fields={["name", "supplier_name", "supplier_type", "supplier_group", "mobile_no"]}
      searchField="supplier_name"
      columns={[
        { key: "name", label: "ID" },
        { key: "supplier_name", label: "Name" },
        { key: "supplier_type", label: "Type" },
        { key: "supplier_group", label: "Group" },
        { key: "mobile_no", label: "Mobile" },
      ]}
    />
  );
}
