---
id: session-security
title: Session & Security
sidebar_position: 5
---

# Session & Security

## Login flow

1. Open `/surge` — guest is redirected to the Frappe login page automatically.
2. Enter Frappe credentials → redirected back to `/surge`.
3. **Profile Selector** — pick the POS Profile for this counter.
4. **Cashier PIN screen** — select your name → enter PIN → Sell Screen opens.

## PIN entry

- PIN is 4–8 digits, numeric only.
- Auto-submits on the 4th digit (no confirm button needed).
- Each wrong attempt shows "X attempts left".
- **3 wrong attempts** → account locked for 5 minutes; PIN pad disabled with countdown.

## Session persistence

| Event | Result |
|---|---|
| F5 / hard refresh | SellScreen reloads immediately — no PIN re-entry |
| Session TTL expires (12 h) | Dropped back to Cashier PIN screen |
| Tab close | Back to Cashier PIN screen (session storage is tab-scoped) |

## Idle lock

- **14 min 45 sec** of inactivity → warning banner: "Terminal will lock in 15s"
- Click **I'm here** to dismiss and reset the 15-minute timer
- At exactly 15 min → locked back to Cashier PIN screen

## Lock terminal

Click the **Lock** button in the navbar at any time. Returns to the Cashier PIN screen. The Frappe session stays open — the next cashier just enters their PIN.

## Logout

Click **Logout** in the navbar → confirm. This ends the Frappe session. The next user must sign in with Frappe credentials.

## Session expired overlay

If another tab calls logout (or the session times out on the server), the next API call shows a dark overlay: **"Session expired — your cart is saved"**. Click **Sign in again** to re-authenticate. The cart is not lost while the tab is still open.

## Lockout override

If a cashier is locked (3 wrong PINs), a Manager can clear the lockout:

1. Log in as Manager on the same terminal.
2. Call `surge.api.auth.override_lockout` with the Manager's PIN and the locked user's ID.
3. Locked account cleared — cashier can try again.
