/**
 * Group H — Frontend: ShiftOpen scenarios
 *
 * H1: Stale session from a previous day → amber warning banner is shown
 * H2: Empty payment_modes on profile → error message shown, not blank form
 *
 * These tests use Playwright's route interception (no MSW dependency) to
 * mock the Frappe API responses exactly as the backend would return them.
 */

import { test, expect } from "@playwright/test";

// ── Shared mock builders ───────────────────────────────────────────────────

const mockConfig = {
  pos_profile: "TestProfile",
  user: "cashier@test.com",
  full_name: "Test Cashier",
  has_desk_access: 0,
};

function mockPOSProfile(paymentModes: string[] = ["Cash", "UPI"]) {
  return {
    name: "TestProfile",
    company: "Test Company",
    warehouse: "TestWarehouse - TC",
    currency: "INR",
    selling_price_list: "Standard Selling",
    payment_modes: paymentModes,
    allow_discount_change: 1,
    discount_limit_cashier: 5,
    discount_limit_supervisor: 15,
    discount_limit_manager: 100,
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

// ── Route interception helper ─────────────────────────────────────────────

async function interceptAPI(
  page: import("@playwright/test").Page,
  responses: Record<string, unknown>,
) {
  await page.route("**/api/method/**", async (route) => {
    const url = route.request().url();
    for (const [key, value] of Object.entries(responses)) {
      if (url.includes(key)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ message: value }),
        });
        return;
      }
    }
    await route.fulfill({
      status: 404,
      body: JSON.stringify({ message: null }),
    });
  });
}

// ── H1: Stale session amber banner ────────────────────────────────────────

test("H1: stale session shows amber warning banner", async ({ page }) => {
  await interceptAPI(page, {
    // get_active_session returns stale: true (session from yesterday)
    "surge.api.session.get_active_session": { session: null, stale: true },
    // Profile is valid with payment modes
    "surge.api.session.get_pos_profile": mockPOSProfile(),
    // Cashier data
    "surge.api.auth.get_cashiers": { cashiers: [mockCashier()] },
  });

  // Navigate to the POS app — replace with your actual route
  await page.goto("/");

  // Wait for ShiftOpen to render (after PIN screen)
  // The stale banner should appear within the shift open card
  const staleBanner = page.locator("text=shift from a previous day").or(
    page.locator("[data-testid='stale-session-warning']"),
  );

  // Use amber styling as a fallback selector (robust against text changes)
  const amberBanner = page.locator(".bg-amber-50, .border-amber-200").first();

  await expect(amberBanner).toBeVisible({ timeout: 10_000 });
});

// ── H2: Empty payment_modes shows error guard ─────────────────────────────

test("H2: empty payment_modes shows error message, not blank form", async ({ page }) => {
  await interceptAPI(page, {
    "surge.api.session.get_active_session": { session: null, stale: false },
    "surge.api.session.get_pos_profile": mockPOSProfile([]),  // empty!
    "surge.api.auth.get_cashiers": { cashiers: [mockCashier()] },
  });

  await page.goto("/");

  // Error message must be visible
  const errorMsg = page.locator("text=No payment modes configured").or(
    page.locator(".text-destructive"),
  );
  await expect(errorMsg).toBeVisible({ timeout: 10_000 });

  // The numeric input fields must NOT be present (form should not render)
  const inputs = page.locator("input[type='number']");
  await expect(inputs).toHaveCount(0);
});

// ── H2-sanity: With valid modes, form renders correctly ───────────────────

test("H2-sanity: valid payment_modes renders input fields", async ({ page }) => {
  await interceptAPI(page, {
    "surge.api.session.get_active_session": { session: null, stale: false },
    "surge.api.session.get_pos_profile": mockPOSProfile(["Cash", "UPI"]),
    "surge.api.auth.get_cashiers": { cashiers: [mockCashier()] },
  });

  await page.goto("/");

  // Two numeric inputs should exist (one per payment mode)
  const inputs = page.locator("input[type='number']");
  await expect(inputs).toHaveCount(2, { timeout: 10_000 });

  // Submit button should be present and enabled
  const submitBtn = page.locator("button:has-text('Open Shift')");
  await expect(submitBtn).toBeVisible();
  await expect(submitBtn).toBeEnabled();
});
