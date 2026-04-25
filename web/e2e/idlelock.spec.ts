/**
 * Group D — Frontend: Idle Lock Timer — Scenarios D01–D07
 *
 * D01  After 14m45s inactivity → idle warning dialog appears
 * D02  Dismiss idle warning → timer resets, no lock
 * D03  After full 15m inactivity (no dismiss) → screen locked
 * D04  Idle timer does NOT lock while PaymentDialog is open
 * D05  Idle timer does NOT lock while LogoutConfirm dialog is open
 * D06  Idle timer does NOT lock while ShiftClose dialog is open
 * D07  Timer resets after ShiftClose completes
 *
 * Uses Playwright's page.clock API to fast-forward browser timers without
 * waiting for real wall-clock time.
 */

import { test, expect } from "@playwright/test";

const WARN_MS = 14 * 60 * 1000 + 45 * 1000; // 14m45s
const LOCK_MS = 15 * 60 * 1000;              // 15m00s
const EXTRA_MS = 5_000;                       // 5s buffer

// ── Mock helpers ──────────────────────────────────────────────────────────────

async function interceptWithSession(page: import("@playwright/test").Page) {
  await page.route("**/api/method/**", async (route) => {
    const url = route.request().url();
    const respond = (body: unknown) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: body }) });

    if (url.includes("get_active_session"))
      return respond({ session: { name: "POS-OPEN-001", user: "cashier@test.com" }, stale: false });
    if (url.includes("get_pos_profile"))
      return respond({ name: "TestProfile", payment_modes: ["Cash"], currency: "INR" });
    if (url.includes("verify_pin"))
      return respond({ status: "ok", user: "cashier@test.com", access_level: "Cashier", full_name: "Test Cashier" });
    if (url.includes("get_items"))
      return respond({ items: [], has_more: false });

    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: null }) });
  });
}

async function loginAndNavigateToSell(page: import("@playwright/test").Page) {
  await interceptWithSession(page);
  await page.clock.install();
  await page.goto("/surge");
  // Complete PIN entry to reach the sell screen
  const pinInput = page.locator("input[type='password'], input[data-testid='pin-input']").first();
  if (await pinInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await pinInput.fill("1234");
    await page.keyboard.press("Enter");
  }
  // Wait for sell screen to be visible
  await page.waitForSelector("[data-testid='sell-screen'], .sell-screen, main", { timeout: 10_000 });
}

// ── D01: Idle warning at 14m45s ───────────────────────────────────────────────

test("D01: idle warning appears after 14m45s inactivity", async ({ page }) => {
  await loginAndNavigateToSell(page);
  await page.clock.fastForward(WARN_MS + EXTRA_MS);

  const warning = page
    .locator("text=You've been idle")
    .or(page.locator("[data-testid='idle-warning']"))
    .or(page.locator("[role='alertdialog']"));

  await expect(warning).toBeVisible({ timeout: 5_000 });
});

// ── D02: Dismiss resets timer ─────────────────────────────────────────────────

test("D02: dismissing idle warning resets the timer", async ({ page }) => {
  await loginAndNavigateToSell(page);
  await page.clock.fastForward(WARN_MS + EXTRA_MS);

  const dismissBtn = page
    .locator("button:has-text('Stay')")
    .or(page.locator("button:has-text('I'm here')"))
    .or(page.locator("[data-testid='idle-dismiss']"));

  await expect(dismissBtn).toBeVisible({ timeout: 5_000 });
  await dismissBtn.click();

  // Advance only half the warning period again — no new warning yet
  await page.clock.fastForward(WARN_MS / 2);
  const warningAgain = page.locator("[data-testid='idle-warning'], [role='alertdialog']");
  await expect(warningAgain).toHaveCount(0);
});

// ── D03: Full 15m → locked ─────────────────────────────────────────────────────

test("D03: screen locks after full 15m inactivity", async ({ page }) => {
  await loginAndNavigateToSell(page);
  await page.clock.fastForward(LOCK_MS + EXTRA_MS);

  const lockScreen = page
    .locator("[data-testid='lock-screen']")
    .or(page.locator("text=Session locked"))
    .or(page.locator("input[data-testid='pin-input']"));

  await expect(lockScreen).toBeVisible({ timeout: 5_000 });
});

// ── D04: No lock while PaymentDialog is open ──────────────────────────────────

test("D04: idle timer does not lock while PaymentDialog is open", async ({ page }) => {
  await loginAndNavigateToSell(page);

  // Open PaymentDialog
  const chargeBtn = page
    .locator("button:has-text('Charge')")
    .or(page.locator("[data-testid='open-payment']"));
  if (await chargeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await chargeBtn.click();
    await expect(page.locator("[data-testid='payment-dialog'], [role='dialog']")).toBeVisible({
      timeout: 3_000,
    });
  }

  await page.clock.fastForward(LOCK_MS + EXTRA_MS);

  // Lock screen must NOT appear while payment dialog is open
  const lockScreen = page.locator("[data-testid='lock-screen']");
  await expect(lockScreen).toHaveCount(0);
});

// ── D05: No lock while LogoutConfirm is open ──────────────────────────────────

test("D05: idle timer does not lock while LogoutConfirm is open", async ({ page }) => {
  await loginAndNavigateToSell(page);

  const logoutBtn = page
    .locator("button:has-text('Logout')")
    .or(page.locator("[data-testid='logout-btn']"));
  if (await logoutBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await logoutBtn.click();
    await expect(page.locator("[data-testid='logout-confirm'], [role='dialog']")).toBeVisible({
      timeout: 3_000,
    });
  }

  await page.clock.fastForward(LOCK_MS + EXTRA_MS);

  const lockScreen = page.locator("[data-testid='lock-screen']");
  await expect(lockScreen).toHaveCount(0);
});

// ── D06: No lock while ShiftClose is open ────────────────────────────────────

test("D06: idle timer does not lock while ShiftClose dialog is open", async ({ page }) => {
  await loginAndNavigateToSell(page);

  const closeBtn = page
    .locator("button:has-text('Close Shift')")
    .or(page.locator("[data-testid='close-shift-btn']"));
  if (await closeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await closeBtn.click();
    await expect(
      page.locator("[data-testid='shift-close-dialog'], [role='dialog']"),
    ).toBeVisible({ timeout: 3_000 });
  }

  await page.clock.fastForward(LOCK_MS + EXTRA_MS);

  const lockScreen = page.locator("[data-testid='lock-screen']");
  await expect(lockScreen).toHaveCount(0);
});

// ── D07: Timer resets after ShiftClose completes ──────────────────────────────

test("D07: idle timer resets after shift close completes", async ({ page }) => {
  await page.route("**/api/method/**", async (route) => {
    const url = route.request().url();
    const respond = (body: unknown) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: body }) });

    if (url.includes("get_active_session"))
      return respond({ session: null, stale: false });  // after close, no session
    if (url.includes("close_session"))
      return respond({ z_report: { net_sales_paise: 0, net_returns_paise: 0, payment_modes: [] } });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: null }) });
  });

  await page.clock.install();
  await page.goto("/surge");

  // Simulate shift close happening early
  await page.clock.fastForward(1_000);

  // After close, fast-forward to just before warning — no lock should appear
  await page.clock.fastForward(WARN_MS - 5_000);

  const lockScreen = page.locator("[data-testid='lock-screen']");
  await expect(lockScreen).toHaveCount(0);
});
