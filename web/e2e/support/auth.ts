import type { Page } from "@playwright/test";

export interface SessionOptions {
  paymentModes?: string[];
  accessLevel?: string;
}

/**
 * Injects window.SURGE_CONFIG and sessionStorage cashier session before page.goto().
 * Without this, App sees isGuest=true and renders LoginScreen instead of SellScreen.
 */
export async function injectCashierSession(page: Page, options: SessionOptions = {}) {
  const { paymentModes = ["Cash", "UPI"], accessLevel = "Cashier" } = options;
  const loginAt = Date.now(); // evaluated in Node.js, serialized to JSON

  await page.addInitScript(
    ({ key, data, cfg }: { key: string; data: object; cfg: object }) => {
      sessionStorage.setItem(key, JSON.stringify(data));
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).SURGE_CONFIG = cfg;
    },
    {
      key: "surge:cashier_session",
      data: {
        profile: {
          name: "TestProfile",
          payment_modes: paymentModes,
          currency: "INR",
          warehouse: "TestWarehouse - TC",
          selling_price_list: "Standard Selling",
          allow_discount_change: 1,
          discount_limit_cashier: 5,
          discount_limit_supervisor: 15,
          discount_limit_manager: 100,
        },
        cashier: {
          user: "cashier@test.com",
          full_name: "Test Cashier",
          access_level: accessLevel,
          has_pin: true,
          locked: false,
        },
        loginAt,
      },
      cfg: { user: "cashier@test.com", full_name: "Test Cashier", has_desk_access: 0, csrf_token: "" },
    },
  );
}
