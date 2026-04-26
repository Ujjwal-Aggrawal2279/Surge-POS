import {
  LayoutDashboard, Package, PackagePlus, PackageX, RefreshCcw,
  Tag, Bookmark, Warehouse, ShoppingCart, ClipboardCheck,
  Receipt, Building2, Users, Truck, Settings2, MonitorCheck,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SidebarPermissions, DashboardPage } from "@/types/pos";

interface NavItem {
  id: DashboardPage;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  perm?: keyof SidebarPermissions;
}

const SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Main",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "Inventory",
    items: [
      { id: "products",          label: "Products",           icon: Package,      perm: "item_read" },
      { id: "create-product",    label: "Create Product",     icon: PackagePlus,  perm: "item_create" },
      { id: "disabled-products", label: "Disabled Products",  icon: PackageX,     perm: "item_read" },
      { id: "reordered-products",label: "Reorder Points",     icon: RefreshCcw,   perm: "item_read" },
      { id: "category",          label: "Category",           icon: Tag,          perm: "item_group_create" },
      { id: "brands",            label: "Brands",             icon: Bookmark,     perm: "brand_create" },
    ],
  },
  {
    title: "Stock",
    items: [
      { id: "stock",             label: "Stock Inventory",    icon: Warehouse,        perm: "stock_ledger_read" },
      { id: "purchase-orders",   label: "Purchase Orders",    icon: ShoppingCart,     perm: "purchase_order_read" },
      { id: "purchase-receipts", label: "Purchase Receipts",  icon: ClipboardCheck,   perm: "purchase_receipt_read" },
      { id: "sales-invoices",    label: "Sales Invoices",     icon: Receipt,          perm: "sales_invoice_read" },
      { id: "warehouses",        label: "Warehouses",         icon: Building2,        perm: "warehouse_read" },
    ],
  },
  {
    title: "Peoples",
    items: [
      { id: "customers",   label: "Customers",    icon: Users,     perm: "customer_read" },
      { id: "suppliers",   label: "Suppliers",    icon: Truck,     perm: "supplier_read" },
      { id: "pos-profiles",label: "POS Profiles", icon: Settings2, perm: "pos_profile_read" },
    ],
  },
];

interface Props {
  permissions: SidebarPermissions;
  activePage: DashboardPage;
  onNavigate: (page: DashboardPage) => void;
  onGoToPOS: () => void;
}

export function Sidebar({ permissions, activePage, onNavigate, onGoToPOS }: Props) {
  return (
    <aside className="flex h-screen w-62.75 shrink-0 flex-col border-r border-[#E6EAED] bg-white">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-[#E6EAED] px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#6938EF]">
          <span className="text-sm font-black text-white">S</span>
        </div>
        <span className="text-base font-black text-[#212B36]">Surge POS</span>
      </div>

      {/* Nav sections */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {SECTIONS.map((section) => {
          const visible = section.items.filter(
            (item) => !item.perm || permissions[item.perm],
          );
          if (visible.length === 0) return null;
          return (
            <div key={section.title} className="mb-4">
              <p className="mb-1 px-2 text-[10px] font-bold uppercase tracking-widest text-[#919EAB]">
                {section.title}
              </p>
              {visible.map((item) => {
                const active = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onNavigate(item.id)}
                    className={cn(
                      "flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-all duration-150",
                      active
                        ? "bg-[#F4F3FF] font-semibold text-[#6938EF]"
                        : "text-[#637381] hover:translate-x-0.5 hover:bg-[#F4F6F8] hover:text-[#212B36]",
                    )}
                  >
                    <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-[#6938EF]" : "text-[#919EAB]")} />
                    <span className="flex-1 text-left">{item.label}</span>
                    {active && <ChevronRight className="h-3.5 w-3.5 text-[#6938EF]" />}
                  </button>
                );
              })}
            </div>
          );
        })}
      </nav>

      {/* POS Terminal shortcut */}
      <div className="border-t border-[#E6EAED] p-3">
        <button
          type="button"
          onClick={onGoToPOS}
          className="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-semibold text-[#637381] transition-all duration-150 hover:translate-x-0.5 hover:bg-[#F4F6F8] hover:text-[#212B36]"
        >
          <MonitorCheck className="h-4 w-4 shrink-0 text-[#0E9384]" />
          POS Terminal
        </button>
      </div>
    </aside>
  );
}
