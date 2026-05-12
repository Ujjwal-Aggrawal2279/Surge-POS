# Surge POS — Auth, Security & Offline Test Plan

**Date:** 2026-04-24  
**Tester:** Ujjwal  
**Site:** liquorvault.com:8013  
**Users required:** ujjmee2279@gmail.com (Cashier → Manager), pritam@gmail.com (Manager)

---

## How to use this doc

Each test has a **Steps** block and an **Expected** block.  
Mark ✅ pass / ❌ fail / ⏭ skipped next to each test ID.

---

## Section A — Login & Session Bootstrap

### A-01 · Guest redirect
**Steps**
1. Open a new Incognito window → `liquorvault.com:8013/surge`

**Expected**
- Login screen shown (Frappe login form)
- No POS UI visible
- URL stays at `/surge`

---

### A-02 · Frappe login
**Steps**
1. Enter valid credentials → Submit

**Expected**
- Redirected back to `/surge`
- Profile Selector screen shown (not the cashier screen)

---

### A-03 · Profile selection
**Steps**
1. See LV Main Counter card → click it

**Expected**
- Cashier PIN screen shown
- Profile name "LV Main Counter" visible in header

---

### A-04 · Cashier PIN — correct
**Steps**
1. Select "Ujjwal" from cashier list
2. Enter correct 4-digit PIN

**Expected**
- SellScreen loads
- Header shows: `LV Main Counter · Ujjwal`
- Online pill is green

---

### A-05 · Cashier PIN — wrong PIN
**Steps**
1. Select cashier
2. Enter wrong PIN twice

**Expected**
- Each wrong attempt shows "X attempts left"
- Counter decrements correctly

---

### A-06 · PIN lockout (3 wrong attempts)
**Steps**
1. Enter wrong PIN 3 times in a row

**Expected**
- Account locked message shown
- Lockout timer displayed (5 min countdown)
- PIN pad disabled

---

### A-07 · Session persistence across F5
**Steps**
1. Log in as cashier → reach SellScreen
2. Press F5 (hard refresh)

**Expected**
- SellScreen loads immediately — no PIN re-entry
- Same cashier name shown
- Cart is empty (cart is not persisted, that's correct)

---

### A-08 · Session TTL (12 hours)
**Steps**
1. Open DevTools → Application → Session Storage
2. Find key `surge:cashier_session`
3. Edit `loginAt` to a timestamp >12 hours ago → F5

**Expected**
- Dropped back to Cashier PIN screen (session expired)
- `surge:cashier_session` key removed from sessionStorage

---

### A-09 · Tab close clears session
**Steps**
1. Log in → reach SellScreen
2. Close the tab
3. Reopen `liquorvault.com:8013/surge`

**Expected**
- Back to Cashier PIN screen (sessionStorage is tab-scoped)

---

## Section B — Access Control & Discount Flow

### B-01 · Discount button visibility
**Steps**
1. Log in as Ujjwal (Manager on LV Main Counter)
2. Add any item to cart

**Expected**
- "Discount" button in cart action bar is **enabled** (not greyed out)
- Requires `allow_discount_change = 1` on POS Profile

---

### B-02 · Manager — discount within limit (≤100%)
**Steps**
1. Click Discount → enter 10% on the item
2. Click "Apply Discount"

**Expected**
- No approval modal (Manager limit = 100%)
- Item price updates: original − 10%
- Subtotal and Total recalculate correctly

---

### B-03 · Cashier — discount within limit (≤5%)
**Steps**
1. Change Ujjwal's access level to Cashier in DB or log in as a Cashier-level user
2. Add item → Discount → enter 4%
3. Click "Apply Discount"

**Expected**
- Applied directly, no approval needed

---

### B-04 · Cashier — discount exceeds limit (>5%) → remote approval request
**Steps**
1. Logged in as Cashier
2. Add item → Discount → enter 25%
3. "Request Approval" button appears (amber)
4. Click it → select Pritam (Manager) → click "Send Approval Request"

**Expected**
- Modal transitions to spinner: "Waiting for Pritam — request sent to their screen"
- 3-minute countdown starts
- On Pritam's screen (second browser/incognito): bell badge shows `1`

---

### B-05 · Manager — approve remote request
**Steps**
1. On Pritam's SellScreen → click Approvals bell → see Ujjwal's request
2. Click Review → enter Pritam's PIN → click Approve

**Expected**
- Ujjwal's screen instantly shows "Approved by Pritam"
- Discount applied to cart
- Approval queue clears on Pritam's screen

---

### B-06 · Manager — deny remote request
**Steps**
1. Same as B-04 but Pritam clicks Deny after entering PIN

**Expected**
- Ujjwal's screen shows "Request Denied"
- Option to "Try again" visible
- Cart discount NOT applied

---

### B-07 · Approval — 3-minute countdown expires (manager hasn't responded)
**Steps**
1. Send remote approval request
2. Do NOT respond on manager screen
3. Wait 3 minutes

**Expected**
- Cashier screen transitions to hourglass: "Pritam hasn't responded yet — request is still active for 30 minutes"
- Spinner shows "Still checking every 3 seconds…"
- Poll continues in background

---

### B-08 · Manager approves AFTER cashier timer expires
**Steps**
1. Reach the "unanswered" state from B-07
2. Now go to Pritam's screen → approve

**Expected**
- Cashier screen resolves within 3 seconds (poll catches it)
- Discount applied despite timer having expired

---

### B-09 · Page refresh while waiting for approval
**Steps**
1. Send remote approval request (cashier in "waiting" state)
2. Press F5 on cashier screen
3. Re-open Discount modal on the same cart item

**Expected**
- Modal restores to "waiting" state (reqId from sessionStorage)
- Countdown shows approximate remaining time
- Poll resumes immediately

---

### B-10 · Redis unavailable fallback
**Simulate:** Stop Redis → attempt remote approval

**Expected**
- Error state: "Remote approval is temporarily unavailable. Ask the manager to enter their PIN on this screen."
- "Try again" button shown
- Same-screen PIN flow still works (old `request_approval` endpoint)

---

### B-11 · Manager logs in AFTER approval request was sent
**Steps**
1. Send approval request (cashier waiting)
2. On manager's browser: log out of Surge → log back in → reach SellScreen

**Expected**
- Approvals bell immediately shows badge `1` on mount
- Frappe notification bell (top bar) also shows the alert from Notification Log
- Manager can approve → cashier resolves

---

## Section C — Security

### C-01 · HMAC token — tampered token rejected
**Steps**
1. Complete an approval → capture the token in Network tab (DevTools)
2. Modify any character of the token
3. Submit the invoice with the tampered token

**Expected**
- Server returns 403 / validation error: "Invalid approval token"
- Invoice NOT created

---

### C-02 · One-time token — replay prevention
**Steps**
1. Get a valid approval token
2. Submit invoice successfully
3. Try to submit another invoice with the SAME token (copy from Network tab)

**Expected**
- Second submission rejected: token already consumed
- Redis key was deleted after first use

---

### C-03 · Idle lock — 15 minutes
**Steps**
1. Log in → reach SellScreen
2. Stop all mouse/keyboard/touch activity for 14 min 45 sec

**Expected**
- Warning banner appears at 14:45: "Terminal will lock in 15s"
- At 15:00 exactly → locked back to Cashier PIN screen
- "I'm here" button dismisses warning and resets timer

---

### C-04 · Idle lock — dismiss warning
**Steps**
1. Wait for warning banner (step 2 above)
2. Click "I'm here"

**Expected**
- Banner disappears
- Timer resets to 15 minutes from now
- No lock fires

---

### C-05 · Session expired overlay
**Simulate:** In another tab, call `/api/method/logout` → return to POS tab → trigger any API call

**Expected**
- Dark overlay: "Session expired — your cart is saved"
- "Sign in again" button redirects to `/surge`
- Cart state NOT lost (Zustand is in-memory, tab still alive)

---

### C-06 · Lockout override by Manager
**Steps**
1. Lock a cashier account (3 wrong PINs — from C test above)
2. Log in as Manager
3. Use override endpoint or PIN reset flow

**Expected**
- Locked account cleared
- Cashier can log in again

---

### C-07 · PIN cannot be set by non-Manager
**Steps**
1. Log in as Cashier
2. Attempt to call `surge.api.auth.set_pin` directly from DevTools console

**Expected**
- Returns 403 / PermissionError
- PIN unchanged

---

## Section D — Offline Invoice Flow

> **Setup:** Use Chrome DevTools → Network tab → Offline toggle, or disable your network adapter.

---

### D-01 · Invoice creation while offline
**Steps**
1. Add item to cart → Payment → Charge
2. BEFORE clicking Charge: go DevTools → Network → Offline
3. Click Charge

**Expected**
- Payment success screen shows **WifiOff icon**: "Saved offline — will sync automatically when online"
- Invoice name shown as null / pending
- Cart clears normally

---

### D-02 · IndexedDB queue written
**Steps**
1. After D-01: DevTools → Application → IndexedDB → `surge-offline` → `write_queue`

**Expected**
- One entry exists with `client_request_id` (UUIDv7)
- Entry has full item/payment data

---

### D-03 · Duplicate guard on double-submit
**Steps**
1. While offline: submit same cart twice (e.g. click Charge, navigate back, submit again with same items)

**Expected**
- Only ONE entry in IndexedDB (upsert on `client_request_id`)
- No duplicate invoice when synced

---

### D-04 · Queue syncs on reconnect
**Steps**
1. Go back online (disable Offline mode in DevTools)
2. Wait up to 10 seconds (scheduler runs every ~10s)

**Expected**
- `Surge Write Queue` entry in ERPNext Desk changes from `Pending` → `Done`
- POS Invoice created in ERPNext with correct items/amounts
- IndexedDB entry removed (dequeued after server confirms)

---

### D-05 · Realtime sync confirmation
**Steps**
1. Go back online after offline invoice
2. Watch browser console for `surge:invoice_submitted` event

**Expected**
- Event fires with `invoice_name` and `client_request_id`
- Stock invalidated (cart stock updates within 60s)

---

### D-06 · Retry with exponential backoff
**Simulate:** Make ERPNext temporarily return 500 errors (stop bench worker)

**Expected**
- Write Queue entry status: `Failed`
- `attempt_count` increments with each retry
- `next_retry_at` doubles each attempt (10s → 20s → 40s → 80s → 160s)
- After 5 attempts: status stays `Failed`, no more retries

---

### D-07 · Circuit breaker trips on 10 consecutive failures
**Simulate:** 10+ consecutive queue entries all failing

**Expected**
- Circuit breaker opens: `surge:circuit_open_until` set in Redis for 5 min
- `flush_write_queue` exits early (no processing) while breaker is open
- `surge:circuit_breaker_tripped` realtime event fires
- After 5 min: breaker auto-resets, processing resumes

---

### D-08 · Stock conflict detection
**Simulate:**
1. Offline: sell last 2 bottles of HOEGAARDEN
2. While offline: also sell 2 bottles from another terminal (depletes stock to 0)
3. Reconnect

**Expected**
- First terminal's queue entry: status `Conflict`
- `Surge Sync Conflict` DocType record created in ERPNext
- `surge:conflict_created` realtime event fires
- `conflict_type` = "Insufficient Stock"

---

### D-09 · Conflict resolution — Force Submit
**Steps**
1. Open ERPNext Desk → Surge Sync Conflict → open the conflicted entry
2. Set resolution to "Approved — Force Submit" → Save

**Expected**
- Invoice created with `allow_negative_stock = 1` temporarily
- Stock Settings restored to original after submit
- Conflict marked as resolved

---

### D-10 · Conflict resolution — Void
**Steps**
1. Open conflict → set "Rejected — Void"

**Expected**
- No invoice created
- Conflict closed with `resolved_by` and `resolved_at` populated

---

## Section E — Realtime Sync

### E-01 · Item disabled → tombstone propagates
**Steps**
1. In ERPNext Desk: open any item → tick Disabled → Save
2. Watch POS grid (within 60s)

**Expected**
- Item disappears from POS grid
- Redis tombstone set: `surge:tombstones` ZSET contains the item_code

---

### E-02 · Item deleted → tombstone propagates
**Steps**
1. Delete an item from ERPNext Desk (trash it)
2. Watch POS grid

**Expected**
- Item removed from grid within 60s (realtime) or at most 60s (poll fallback)

---

### E-03 · Stock change → POS updates
**Steps**
1. Create a Material Receipt in ERPNext for any item
2. Submit it
3. Watch POS — hover over item card to see stock badge

**Expected**
- Stock badge updates within 30s
- `Stock Ledger Entry.on_submit` hook fires → cache invalidated → frontend refetches

---

### E-04 · Realtime subscription retry (Socket.IO loads async)
**Steps**
1. Hard refresh POS
2. In console: check that `surge:invalidate` listener is registered (no error on load)

**Expected**
- No "frappe.realtime not found" errors
- Subscription registered within 10s (retry loop: 20 × 500ms)

---

### E-05 · Multiple terminal coalescing (anti-stampede)
**Simulate:** Open 5 browser tabs, all on SellScreen. Update an item in ERPNext.

**Expected**
- All 5 tabs refetch items/prices
- Refetches are staggered (0–1500ms random jitter) — not simultaneous
- Only 1 realtime event published from server (SETNX gate, 1s window)

---

## Section F — Barcode / Item Search

### F-01 · Item code search
**Steps**
1. Type exact item_code (e.g. `HOEGAARDEN NECTARINE BEER-500ML`) in search box
2. Press Enter

**Expected**
- Item added to cart immediately
- Search box clears

---

### F-02 · Barcode search
**Steps**
1. Type exact barcode (e.g. `8902246014891`) in search box
2. Press Enter

**Expected**
- Matching item added to cart
- Search box clears

---

### F-03 · LV-prefix barcode (case-insensitive)
**Steps**
1. Type `lv2024006` (lowercase) in search box
2. Press Enter

**Expected**
- HEINEKEN SILVER BEER-650ML added to cart (barcode is `LV2024006`)
- Case-insensitive match works

---

### F-04 · Partial search — no auto-add
**Steps**
1. Type `HOEG` in search box
2. Press Enter

**Expected**
- Grid filters to matching items
- Nothing added to cart (no exact match)

---

## Section G — Payment Dialog

### G-01 · Cash tendered — change calculation
**Steps**
1. Add item ₹300 → Payment → select Cash
2. Enter ₹500 in "Cash Tendered"

**Expected**
- Change: ₹200.00 shown in green
- "Charge" button enabled

---

### G-02 · Cash tendered — short
**Steps**
1. Enter ₹200 tendered for ₹300 bill

**Expected**
- "Short by ₹100.00" shown in red
- "Charge" button disabled

---

### G-03 · Non-cash payment — no tendered field
**Steps**
1. Select Card or UPI

**Expected**
- Cash tendered input hidden
- Charge button enabled immediately

---

### G-04 · Offline payment — success state
**Steps**
1. Go offline → complete payment

**Expected**
- WifiOff icon shown
- "Saved offline — will sync automatically when online"
- "New Sale" button clears cart

---

## Test Summary Checklist

| Section | Tests | Pass | Fail | Skip |
|---------|-------|------|------|------|
| A — Login & Session | 9 | | | |
| B — Access Control & Discount | 11 | | | |
| C — Security | 7 | | | |
| D — Offline Invoice | 10 | | | |
| E — Realtime Sync | 5 | | | |
| F — Barcode Search | 4 | | | |
| G — Payment Dialog | 4 | | | |
| **Total** | **50** | | | |

---

## Known limitations (not bugs)

- Cart is NOT persisted across tab close (sessionStorage only) — by design
- Offline approval tokens are not supported — discount approvals require network
- Circuit breaker cooldown is 5 min — invoices queue but do not process during cooldown
- Manager cannot approve from mobile phone — Surge POS requires a desktop/tablet browser session
