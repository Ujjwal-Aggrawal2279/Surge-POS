---
id: payments
title: Payments
sidebar_position: 8
---

# Payments

## Payment dialog

1. Select a payment method tile: **Cash / Card / UPI / Points / Deposit / Cheque**.
2. For **Cash**: enter amount tendered.
   - Change due shown in green when tendered ≥ total.
   - "Short by ₹X" shown in red when tendered < total — **Charge** button stays disabled.
3. For all other methods: no tendered field — **Charge** enabled immediately.
4. Click **Charge** → invoice submitted to ERPNext → success screen shows invoice number.
5. Click **New Sale** to clear the cart.

## Payment validation

The server enforces the following on every invoice:

| Rule | Behaviour |
|---|---|
| At least one payment entry required | Zero-payment submissions are rejected |
| `amount > 0` per payment entry | Zero or negative amounts are rejected |
| Payment mode must be configured on POS Profile | Unrecognised modes are rejected |
| `paid_amount ≤ grand_total` | Overpayment is rejected |
| Shortfall ≤ `write_off_limit` (default ₹1) | Shortfalls beyond the tolerance are rejected — cashier must collect the full amount |

The `write_off_limit` on the POS Profile absorbs sub-₹1 GST rounding differences between client-computed and server-computed totals. It is not a mechanism for partial payment.

## Offline payments

If the server is unreachable when **Charge** is clicked:

- Success screen shows a **WifiOff** icon: "Saved offline — will sync automatically when online."
- Invoice is queued in IndexedDB with a unique request ID.
- Cart clears normally — the cashier can continue selling.
- When connectivity returns, the queue syncs automatically (within ~10 seconds).

Offline-queued invoices are replayed by the server-side sync engine even if the shift has been closed by the time connectivity is restored.

## Success screen

| Icon | Meaning |
|---|---|
| ✅ Green circle | Invoice submitted to ERPNext successfully |
| 📶 WifiOff | Saved offline — will sync |
