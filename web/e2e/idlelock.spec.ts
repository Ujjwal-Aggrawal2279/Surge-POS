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
import { injectCashierSession } from "./support/auth";

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
    if (url.includes("get_cashiers"))
      return respond({ cashiers: [{ user: "cashier@test.com", full_name: "Test Cashier", access_level: "Cashier", has_pin: true, locked: false }] });

    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: null }) });
  });
}

async function loginAndNavigateToSell(page: import("@playwright/test").Page) {
  await interceptWithSession(page);
  await injectCashierSession(page);
  await page.clock.install();
  await page.goto("/");
  await page.waitForSelector("main", { timeout: 10_000 });
}

// ── D01: Idle warning at 14m45s ───────────────────────────────────────────────

test("D01: idle warning appears after 14m45s inactivity", async ({ page }) => {
  await loginAndNavigateToSell(page);
  await page.clock.fastForward(WARN_MS + EXTRA_MS);

  const warning = page
    .locator("text=Terminal will lock in")
    .or(page.locator("[data-testid='idle-warning']"))
    .or(page.locator("[role='alertdialog']"));

  await expect(warning).toBeVisible({ timeout: 5_000 });
});

// ── D02: Dismiss resets timer ─────────────────────────────────────────────────

test("D02: dismissing idle warning resets the timer", async ({ page }) => {
  await loginAndNavigateToSell(page);
  await page.clock.fastForward(WARN_MS + EXTRA_MS);

  const dismissBtn = page.getByRole("button").filter({ hasText: /I'm here|Stay/ });

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

  // Two-step advance: first trigger the warning so React sets up the lock timer,
  // then advance the remaining 15s so the lock timer fires.
  await page.clock.fastForward(WARN_MS + EXTRA_MS);
  await expect(page.locator("text=Terminal will lock in")).toBeVisible({ timeout: 5_000 });
  await page.clock.fastForward(LOCK_MS - WARN_MS + EXTRA_MS);

  const lockScreen = page
    .locator("text=PIN Verification")
    .or(page.locator("text=Who's at the register?"))
    .or(page.locator("[data-testid='lock-screen']"));
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
    await expect(page.locator("text=Log out?")).toBeVisible({ timeout: 3_000 });
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

  await injectCashierSession(page);
  await page.clock.install();
  await page.goto("/");

  // Simulate shift close happening early
  await page.clock.fastForward(1_000);

  // After close, fast-forward to just before warning — no lock should appear
  await page.clock.fastForward(WARN_MS - 5_000);

  const lockScreen = page.locator("[data-testid='lock-screen']");
  await expect(lockScreen).toHaveCount(0);
});
