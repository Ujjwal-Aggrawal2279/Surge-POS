export interface Item {
  item_code: string;
  item_name: string;
  item_group: string;
  brand: string | null;
  stock_uom: string;
  has_variants: 0 | 1;
  image: string | null;
  modified: string;
  barcodes: string[];
}

export interface ItemPrice {
  item_code: string;
  price_list_rate: number;
  currency: string;
  price_list: string;
  modified: string;
}

export interface StockEntry {
  item_code: string;
  warehouse: string;
  actual_qty: number;
  reserved_qty: number;
  modified: string;
}

export interface Customer {
  customer_id: string;
  customer_name: string;
  mobile_no: string | null;
  email_id: string | null;
  gstin: string | null;
  customer_group: string;
  modified: string;
}

export interface CartItem {
  item_code: string;
  item_name: string;
  qty: number;
  rate_paise: number;
  discount_paise: number;
  warehouse: string;
}

export interface PaymentEntry {
  mode_of_payment: string;
  amount_paise: number;
}

export type InvoiceStatus = "submitted" | "queued" | "failed";

export interface CreateInvoiceRequest {
  client_request_id: string;
  pos_profile: string;
  customer: string;
  items: {
    item_code: string;
    qty: number;
    rate_paise: number;
    discount_paise: number;
    warehouse: string | null;
  }[];
  payments: PaymentEntry[];
  offline: boolean;
  approval_token?: string | null;
}

export interface SyncQueueStatus {
  pending: number;
  syncing: number;
  done: number;
  failed: number;
}

export interface SurgeConfig {
  csrf_token: string;
  user: string;
  user_fullname: string;
  site_name: string;
  has_desk_access: 0 | 1;
  socketio_port: number;
}

export interface Cashier {
  user: string;
  full_name: string;
  user_image: string | null;
  has_pin: 0 | 1;
  locked: boolean;
  lockout_until: string | null;
  access_level: "Cashier" | "Supervisor" | "Manager";
}

export interface POSProfile {
  name: string;
  warehouse: string;
  currency: string;
  selling_price_list: string;
  company: string;
  payment_modes: string[];
  allow_discount_change: 0 | 1;
  allow_rate_change: 0 | 1;
  discount_limit_cashier: number;
  discount_limit_supervisor: number;
  discount_limit_manager: number;
}

export interface SidebarPermissions {
  item_read: 0 | 1;
  item_create: 0 | 1;
  item_group_create: 0 | 1;
  brand_create: 0 | 1;
  stock_ledger_read: 0 | 1;
  bin_read: 0 | 1;
  purchase_order_read: 0 | 1;
  purchase_receipt_read: 0 | 1;
  sales_invoice_read: 0 | 1;
  warehouse_read: 0 | 1;
  customer_read: 0 | 1;
  supplier_read: 0 | 1;
  pos_profile_read: 0 | 1;
}

export interface KPIData {
  total_sales: number;
  total_returns: number;
  total_purchase: number;
  purchase_returns: number;
  profit: number;
  outstanding: number;
  expenses: number;
  invoice_count: number;
}

export interface OverviewData {
  customers: number;
  suppliers: number;
  pos_sessions: number;
}

export interface RecentTransaction {
  name: string;
  customer: string;
  posting_date: string;
  status: string;
  grand_total: number;
  is_return: boolean;
}

export interface TopProduct {
  item_code: string;
  item_name: string;
  total_qty: number;
  total_amount: number;
}

export interface LowStockItem {
  item_code: string;
  item_name: string;
  warehouse: string;
  actual_qty: number;
  reorder_level: number;
  reorder_qty: number;
}

export interface DashboardStats {
  currency_symbol: string;
  kpi: KPIData;
  overview: OverviewData;
  recent_transactions: RecentTransaction[];
  top_products: TopProduct[];
  low_stock: LowStockItem[];
}

export interface ChartData {
  labels: string[];
  sales: number[];
  purchases: number[];
}

export type DashboardPage =
  | "dashboard"
  | "products"
  | "create-product"
  | "disabled-products"
  | "reordered-products"
  | "category"
  | "brands"
  | "stock"
  | "purchase-orders"
  | "purchase-receipts"
  | "sales-invoices"
  | "warehouses"
  | "customers"
  | "suppliers"
  | "pos-profiles";

export interface Session {
  name: string;
  period_start_date: string;
  user: string;
}

export interface SessionBalance {
  mode_of_payment: string;
  amount: number;
}

export interface ZReportMode {
  mode_of_payment: string;
  opening_amount_paise: number;
  sales_amount_paise: number;
  expected_amount_paise: number;
  actual_amount_paise: number;
  discrepancy_paise: number;
}

export interface ZReport {
  opening_entry: string;
  pos_profile: string;
  period_start: string;
  period_end: string;
  cashier: string;
  total_invoices: number;
  total_returns: number;
  net_sales_paise: number;
  net_returns_paise: number;
  total_tax_paise: number;
  payment_modes: ZReportMode[];
  discrepancy_reason: string;
}
