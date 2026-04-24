export interface Item {
  item_code: string;
  item_name: string;
  item_group: string;
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
