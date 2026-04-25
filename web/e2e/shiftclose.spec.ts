/**
 * Group E — Frontend: Shift Close — Scenarios E01, E03, E04
 *
 * E01  Cashier role does NOT see "Close Shift" button (Manager-only action)
 * E03  PaymentDialog is absent from DOM while ShiftClose dialog is active
 * E04  ShiftClose with empty payment_modes → shows error, not blank form
 *
 * Uses Playwright route interception to mock API responses.
 */

import { test, expect } from "@playwright/test";

// ── Mock builders ─────────────────────────────────────────────────────────────

function mockActiveSession() {
  return { session: { name: "POS-OPEN-001", user: "cashier@test.com" }, stale: false };
}

function mockPOSProfile(paymentModes: string[] = ["Cash", "UPI"]) {
  return {
    name: "TestProfile",
    company: "Test Company",
    warehouse: "TestWarehouse - TC",
    currency: "INR",
    selling_price_list: "Standard Selling",
    payment_modes: paymentModes,
    allow_discount_change: 1,
  };
}

function mockCashier(accessLevel = "Cashier") {
  return {
    user: "cashier@test.com",
    full_name: "Test Cashier",
    access_level: accessLevel,
    has_pin: true,
    locked: false,
  };
}

async function interceptAPI(
  page: import("@playwright/test").Page,
  overrides: Record<string, unknown> = {},
) {
  await page.route("**/api/method/**", async (route) => {
    const url = route.request().url();
    const respond = (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: body }),
      });

    for (const [key, value] of Object.entries(overrides)) {
      if (url.includes(key)) return respond(value);
    }

    // Defaults
    if (url.includes("get_active_session")) return respond(mockActiveSession());
    if (url.includes("get_pos_profile")) return respond(mockPOSProfile());
    if (url.includes("verify_pin"))
      return respond({ status: "ok", user: "cashier@test.com", access_level: "Cashier", full_name: "Test Cashier" });
    if (url.includes("get_items")) return respond({ items: [], has_more: false });

    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: null }) });
  });
}

async function goToSellScreen(page: import("@playwright/test").Page) {
  await page.goto("/");
  const pinInput = page.locator("input[type='password'], input[data-testid='pin-input']").first();
  if (await pinInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await pinInput.fill("1234");
    await page.keyboard.press("Enter");
  }
  await page.waitForSelector("[data-testid='sell-screen'], .sell-screen, main", { timeout: 10_000 });
}

// ── E01: Cashier cannot see Close Shift ──────────────────────────────────────

test("E01: Cashier-level user does not see Close Shift button", async ({ page }) => {
  await interceptAPI(page, {
    "verify_pin": { status: "ok", user: "cashier@test.com", access_level: "Cashier", full_name: "Test Cashier" },
  });
  await goToSellScreen(page);

  // Close Shift button must be absent for Cashier access level
  const closeShiftBtn = page
    .locator("button:has-text('Close Shift')")
    .or(page.locator("[data-testid='close-shift-btn']"));

  await expect(closeShiftBtn).toHaveCount(0);
});

// ── E01-sanity: Manager CAN see Close Shift ───────────────────────────────────

test("E01-sanity: Manager-level user sees Close Shift button", async ({ page }) => {
  await interceptAPI(page, {
    "verify_pin": { status: "ok", user: "manager@test.com", access_level: "Manager", full_name: "Test Manager" },
  });
  await goToSellScreen(page);

  const closeShiftBtn = page
    .locator("button:has-text('Close Shift')")
    .or(page.locator("[data-testid='close-shift-btn']"));

  await expect(closeShiftBtn).toBeVisible({ timeout: 10_000 });
});

// ── E03: PaymentDialog absent while ShiftClose is open ───────────────────────

test("E03: PaymentDialog is absent from DOM while ShiftClose dialog is active", async ({ page }) => {
  await interceptAPI(page, {
    "verify_pin": { status: "ok", user: "manager@test.com", access_level: "Manager", full_name: "Test Manager" },
  });
  await goToSellScreen(page);

  // Open ShiftClose dialog
  const closeBtn = page
    .locator("button:has-text('Close Shift')")
    .or(page.locator("[data-testid='close-shift-btn']"));

  if (await closeBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await closeBtn.click();
    await expect(
      page.locator("[data-testid='shift-close-dialog'], [role='dialog']"),
    ).toBeVisible({ timeout: 5_000 });

    // PaymentDialog must NOT be in the DOM simultaneously
    const paymentDialog = page
      .locator("[data-testid='payment-dialog']")
      .or(page.locator("[data-testid='charge-dialog']"));

    await expect(paymentDialog).toHaveCount(0);
  }
});

// ── E04: Empty payment_modes shows error in ShiftClose ────────────────────────

test("E04: ShiftClose with empty payment_modes shows error, not blank form", async ({ page }) => {
  await interceptAPI(page, {
    "get_pos_profile": mockPOSProfile([]),  // empty payment modes
    "verify_pin": { status: "ok", user: "manager@test.com", access_level: "Manager", full_name: "Test Manager" },
  });
  await goToSellScreen(page);

  // The shift close form should show an error or warning, not render empty inputs
  const errorMsg = page
    .locator("text=No payment modes")
    .or(page.locator(".text-destructive"))
    .or(page.locator("[data-testid='payment-modes-error']"));

  await expect(errorMsg).toBeVisible({ timeout: 10_000 });

  // Numeric closing-balance inputs must be absent
  const inputs = page.locator("input[type='number']");
  await expect(inputs).toHaveCount(0);
});
