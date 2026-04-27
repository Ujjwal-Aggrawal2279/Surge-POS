import { lazy, Suspense, useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, AlertCircle, Calendar } from "lucide-react";
import kpiTotalSales     from "@/assets/icons/kpi-total-sales.png";
import kpiSalesReturn    from "@/assets/icons/kpi-sales-return.png";
import kpiTotalPurchase  from "@/assets/icons/kpi-total-purchase.png";
import kpiPurchaseReturn from "@/assets/icons/kpi-purchase-return.png";
import statProfit        from "@/assets/icons/stat-profit.png";
import statInvoiceDue    from "@/assets/icons/stat-invoice-due.png";
import statExpenses      from "@/assets/icons/stat-expenses.png";
import statPaymentReturn from "@/assets/icons/stat-payment-returns.png";
import { get } from "@/lib/api";
import { useWidgetsData } from "@/hooks/useWidgetsData";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { KPICard } from "@/components/dashboard/KPICard";
import { StatCard } from "@/components/dashboard/StatCard";
import { SalesChart } from "@/components/dashboard/SalesChart";
import { OverallInfo } from "@/components/dashboard/OverallInfo";
import { CustomerOverview } from "@/components/dashboard/CustomerOverview";
import { TopProducts } from "@/components/dashboard/TopProducts";
import { LowStock } from "@/components/dashboard/LowStock";
import { RecentSales } from "@/components/dashboard/RecentSales";
import type { SidebarPermissions, DashboardStats, DashboardPage } from "@/types/pos";

// Lazy-load sub-pages — cashiers pay zero bundle cost
const ProductsPage         = lazy(() => import("./dashboard/ProductsPage").then((m) => ({ default: () => <m.ProductsPage /> })));
const CreateProductPage    = lazy(() => import("./dashboard/CreateProductPage").then((m) => ({ default: m.CreateProductPage })));
const DisabledPage         = lazy(() => import("./dashboard/ProductsPage").then((m) => ({ default: () => <m.ProductsPage disabled /> })));
const ReorderedPage        = lazy(() => import("./dashboard/ReorderedProductsPage").then((m) => ({ default: m.ReorderedProductsPage })));
const CategoryPage         = lazy(() => import("./dashboard/CategoryPage").then((m) => ({ default: m.CategoryPage })));
const BrandsPage           = lazy(() => import("./dashboard/BrandsPage").then((m) => ({ default: m.BrandsPage })));
const StockInventoryPage   = lazy(() => import("./dashboard/StockInventoryPage").then((m) => ({ default: m.StockInventoryPage })));
const PurchaseOrdersPage   = lazy(() => import("./dashboard/PurchaseOrdersPage").then((m) => ({ default: m.PurchaseOrdersPage })));
const PurchaseReceiptsPage = lazy(() => import("./dashboard/PurchaseReceiptsPage").then((m) => ({ default: m.PurchaseReceiptsPage })));
const SalesInvoicesPage    = lazy(() => import("./dashboard/SalesInvoicesPage").then((m) => ({ default: m.SalesInvoicesPage })));
const WarehousesPage       = lazy(() => import("./dashboard/WarehousesPage").then((m) => ({ default: m.WarehousesPage })));
const CustomersPage        = lazy(() => import("./dashboard/CustomersPage").then((m) => ({ default: m.CustomersPage })));
const SuppliersPage        = lazy(() => import("./dashboard/SuppliersPage").then((m) => ({ default: m.SuppliersPage })));
const POSProfilesPage      = lazy(() => import("./dashboard/POSProfilesPage").then((m) => ({ default: m.POSProfilesPage })));

const PATH_PAGE: Record<string, DashboardPage> = {
  "/surge/dashboard":                    "dashboard",
  "/surge/dashboard/products":           "products",
  "/surge/dashboard/create-product":     "create-product",
  "/surge/dashboard/disabled-products":  "disabled-products",
  "/surge/dashboard/reordered-products": "reordered-products",
  "/surge/dashboard/category":           "category",
  "/surge/dashboard/brands":             "brands",
  "/surge/dashboard/stock":              "stock",
  "/surge/dashboard/purchase-orders":    "purchase-orders",
  "/surge/dashboard/purchase-receipts":  "purchase-receipts",
  "/surge/dashboard/sales-invoices":     "sales-invoices",
  "/surge/dashboard/warehouses":         "warehouses",
  "/surge/dashboard/customers":          "customers",
  "/surge/dashboard/suppliers":          "suppliers",
  "/surge/dashboard/pos-profiles":       "pos-profiles",
};
const PAGE_PATH: Record<DashboardPage, string> = Object.fromEntries(
  Object.entries(PATH_PAGE).map(([path, page]) => [page, path]),
) as Record<DashboardPage, string>;

function pageFromPath(): DashboardPage {
  if (window.location.hash.startsWith("#/dashboard")) {
    const legacy = window.location.hash.replace("#", "");
    return PATH_PAGE[`/surge${legacy}`] ?? "dashboard";
  }
  return PATH_PAGE[window.location.pathname] ?? "dashboard";
}

function today()      { return new Date().toISOString().slice(0, 10); }
function monthStart() {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

interface Props {
  onGoToPOS: () => void;
}

export function DashboardScreen({ onGoToPOS }: Props) {
  const [activePage, setActivePage] = useState<DashboardPage>(pageFromPath);
  const [fromDate, setFromDate]     = useState(monthStart);
  const [toDate,   setToDate]       = useState(today);

  const navigate = useCallback((page: DashboardPage) => {
    const path = PAGE_PATH[page];
    window.history.pushState({ page }, "", path);
    window.location.hash = "";
    setActivePage(page);
  }, []);

  useEffect(() => {
    const onPop = () => setActivePage(pageFromPath());
    window.addEventListener("popstate", onPop);
    if (window.location.hash.startsWith("#/dashboard")) {
      const page = pageFromPath();
      window.history.replaceState({ page }, "", PAGE_PATH[page]);
    }
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const { data: permsData } = useQuery<SidebarPermissions>({
    queryKey: ["sidebar-perms"],
    queryFn: () => get<SidebarPermissions>("surge.api.dashboard.get_sidebar_permissions"),
    staleTime: 300_000,
  });
  const permissions: SidebarPermissions = permsData ?? {
    item_read: 0, item_create: 0, item_group_create: 0, brand_create: 0,
    stock_ledger_read: 0, bin_read: 0, purchase_order_read: 0, purchase_receipt_read: 0,
    sales_invoice_read: 0, warehouse_read: 0, customer_read: 0, supplier_read: 0, pos_profile_read: 0,
  };

  // Date-filtered: KPI + stat cards only
  const { data: statsData, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats", fromDate, toDate],
    queryFn: () => get<DashboardStats>("surge.api.dashboard.get_dashboard_stats", { from_date: fromDate, to_date: toDate }),
    staleTime: 120_000,
    enabled: activePage === "dashboard",
  });

  // All-time widgets data — independent of date filter; shared across widget components
  const { data: widgetsData } = useWidgetsData();

  return (
    <div className="flex h-screen overflow-hidden bg-[#FBFBFB]">
      <Sidebar
        permissions={permissions}
        activePage={activePage}
        onNavigate={navigate}
        onGoToPOS={onGoToPOS}
      />

      <main className="dashboard-main flex-1 overflow-y-auto overscroll-contain scroll-smooth">
        {activePage === "dashboard" ? (
          <div className="space-y-4 p-6">

            {/* Header — Figma: "Welcome, Admin" + date range chip */}
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-[28px] font-bold text-[#212b36]">
                  Welcome, {window.SURGE_CONFIG?.user_fullname || "Admin"}
                </h1>
                <p className="text-sm text-[#646b72]">
                  You have{" "}
                  <strong className="text-[#212b36]">
                    {statsData?.kpi.invoice_count ?? "—"}+
                  </strong>{" "}
                  Orders, Today
                </p>
              </div>

              {/* Date range chip — affects KPI + stat cards only */}
              <div className="flex items-center gap-2 rounded-lg border border-[#E6EAED] bg-white px-3 py-2">
                <Calendar className="h-4 w-4 shrink-0 text-[#092c4c]" />
                <div className="flex items-center gap-1.5 text-sm text-[#092c4c]">
                  <label className="relative cursor-pointer">
                    <span>{fmtDate(fromDate)}</span>
                    <input
                      type="date"
                      title="From date"
                      value={fromDate}
                      onChange={(e) => setFromDate(e.target.value)}
                      className="absolute inset-0 cursor-pointer opacity-0"
                    />
                  </label>
                  <span className="text-[#919EAB]">–</span>
                  <label className="relative cursor-pointer">
                    <span>{fmtDate(toDate)}</span>
                    <input
                      type="date"
                      title="To date"
                      value={toDate}
                      onChange={(e) => setToDate(e.target.value)}
                      className="absolute inset-0 cursor-pointer opacity-0"
                    />
                  </label>
                </div>
              </div>
            </div>

            {/* Notification bar — driven by all-time low stock data */}
            {(widgetsData?.low_stock.length ?? 0) > 0 && (
              <div className="flex items-center gap-3 rounded-lg border border-[#f5c6ae] bg-[#fcefea] px-4 py-2.5 text-sm font-semibold text-[#e04f16]">
                <AlertCircle className="h-4 w-4 shrink-0 text-[#e04f16]" />
                <span>
                  Your product is running Low, already below{" "}
                  <strong>{widgetsData!.low_stock.length}</strong> item(s) at reorder level.{" "}
                  <button type="button" onClick={() => navigate("stock")} className="underline">
                    Add Stock
                  </button>
                </span>
              </div>
            )}

            {statsLoading ? (
              <div className="flex items-center justify-center py-24">
                <Loader2 className="h-8 w-8 animate-spin text-[#6938EF]" />
              </div>
            ) : statsData ? (
              <>
                {/* KPI cards — date-filtered */}
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                  <KPICard title="Total Sales"           amount={statsData.kpi.total_sales}      bg="#fe9f43" imgSrc={kpiTotalSales}     trendPct={22}  currency={statsData.currency_symbol} />
                  <KPICard title="Total Sales Return"    amount={statsData.kpi.total_returns}    bg="#092c4c" imgSrc={kpiSalesReturn}    trendPct={-22} currency={statsData.currency_symbol} />
                  <KPICard title="Total Purchase"        amount={statsData.kpi.total_purchase}   bg="#0e9384" imgSrc={kpiTotalPurchase}  trendPct={-22} currency={statsData.currency_symbol} />
                  <KPICard title="Total Purchase Return" amount={statsData.kpi.purchase_returns} bg="#155eef" imgSrc={kpiPurchaseReturn} trendPct={-22} currency={statsData.currency_symbol} />
                </div>

                {/* Stat cards — date-filtered */}
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                  <StatCard title="Profit"          amount={statsData.kpi.profit}       imgSrc={statProfit}        iconBg="bg-[#eef2ff]" currency={statsData.currency_symbol} />
                  <StatCard title="Invoice Due"     amount={statsData.kpi.outstanding}  imgSrc={statInvoiceDue}    iconBg="bg-[#eef8f7]" currency={statsData.currency_symbol} />
                  <StatCard title="Total Expenses"  amount={statsData.kpi.expenses}     imgSrc={statExpenses}      iconBg="bg-[#fff7ee]" currency={statsData.currency_symbol} />
                  <StatCard title="Payment Returns" amount={statsData.kpi.total_returns} imgSrc={statPaymentReturn} iconBg="bg-[#fff0ee]" currency={statsData.currency_symbol} />
                </div>
              </>
            ) : null}

            {/* ── Section 2 — all widgets independent of date filter ── */}

            {/* Chart + right panel (OverallInfo + CustomerOverview as one card) */}
            <div className="flex gap-4">
              <SalesChart />
              <div className="flex w-75 shrink-0 flex-col overflow-hidden rounded-2xl border border-[#E6EAED] bg-white shadow-sm">
                <OverallInfo />
                <CustomerOverview />
              </div>
            </div>

            {/* Widgets row — 3 columns */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <TopProducts />
              <LowStock onNavigate={navigate} />
              <RecentSales />
            </div>

          </div>
        ) : (
          <div className="p-6">
            <Suspense fallback={<div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>}>
              {activePage === "products"            && <ProductsPage />}
              {activePage === "create-product"      && <CreateProductPage />}
              {activePage === "disabled-products"   && <DisabledPage />}
              {activePage === "reordered-products"  && <ReorderedPage />}
              {activePage === "category"            && <CategoryPage />}
              {activePage === "brands"              && <BrandsPage />}
              {activePage === "stock"               && <StockInventoryPage />}
              {activePage === "purchase-orders"     && <PurchaseOrdersPage />}
              {activePage === "purchase-receipts"   && <PurchaseReceiptsPage />}
              {activePage === "sales-invoices"      && <SalesInvoicesPage />}
              {activePage === "warehouses"          && <WarehousesPage />}
              {activePage === "customers"           && <CustomersPage />}
              {activePage === "suppliers"           && <SuppliersPage />}
              {activePage === "pos-profiles"        && <POSProfilesPage />}
            </Suspense>
          </div>
        )}
      </main>
    </div>
  );
}
