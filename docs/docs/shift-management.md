---
id: shift-management
title: Shift Management
sidebar_position: 9
---

# Shift Management

## Opening a shift

1. Log in with Frappe credentials → select POS Profile → enter cashier PIN.
2. **Open Session** dialog appears — enter opening cash balance per denomination.
3. Submit → Shift opens; you land on the Sell Screen.

**Rules:**
- Only one active session per profile at a time. A second attempt while a session is open is rejected with an error — close the existing session first.
- Only **Active** users on the POS Profile can open a shift (Inactive users are denied at the API level).
- A profile with all users set to Inactive cannot be opened by anyone.

:::info Shift required to sell
Invoices cannot be submitted without an open shift. The API rejects real-time sales if no POS Opening Entry is active for the profile. Invoices that were recorded offline during a valid session and queued for later sync are replayed automatically when connectivity returns, even if the session has since closed.
:::

## Stale sessions

If a session was opened on a previous calendar day and never closed, `get_active_session` returns it with `stale: true`. The UI prompts the manager to close it before the new shift can begin.

## Closing a shift (Z-report)

1. Click **Close Shift** in the navbar.
2. **Count your cash** — enter physical cash counted per denomination.
3. Submit → Surge calculates:

| Field | Calculation |
|---|---|
| Expected cash | Sum of all Cash payments recorded during shift |
| Actual cash | Denominations entered in closing dialog |
| Discrepancy | Actual − Expected (negative = short, positive = over) |

4. A **Z-report** is generated and stored. The shift is marked closed.

**Payment mode union:** Closing tallies all payment modes that appear in either the opening balance or the shift's invoices — no mode is silently dropped.

**Midnight-crossing shifts:** Sessions that span midnight correctly attribute invoices to the shift regardless of day boundary.

## Access control for close

| Role | Can close session? |
|---|---|
| Manager | Yes |
| System Manager | Yes |
| Administrator | Yes |
| Supervisor | No |
| Cashier | No |

## Concurrent close

If two browser tabs attempt to close the same session simultaneously, exactly one succeeds. The second gets an error: "Session already closed."

## Paise precision

All monetary amounts are stored and compared in integer paise (1 INR = 100 paise) to avoid floating-point rounding. Discrepancy calculations are exact.
