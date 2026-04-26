import { GenericListPage } from "./GenericListPage";

export function CustomersPage() {
  return (
    <GenericListPage
      title="Customers"
      doctype="Customer"
      fields={["name", "customer_name", "customer_type", "customer_group", "mobile_no"]}
      searchField="customer_name"
      columns={[
        { key: "name", label: "ID" },
        { key: "customer_name", label: "Name" },
        { key: "customer_type", label: "Type" },
        { key: "customer_group", label: "Group" },
        { key: "mobile_no", label: "Mobile" },
      ]}
    />
  );
}
