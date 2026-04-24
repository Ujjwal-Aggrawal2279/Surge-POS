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

## Offline payments

If the server is unreachable when **Charge** is clicked:

- Success screen shows a **WifiOff** icon: "Saved offline — will sync automatically when online."
- Invoice is queued in IndexedDB with a unique request ID.
- Cart clears normally — the cashier can continue selling.
- When connectivity returns, the queue syncs automatically (within ~10 seconds).

## Success screen

| Icon | Meaning |
|---|---|
| ✅ Green circle | Invoice submitted to ERPNext successfully |
| 📶 WifiOff | Saved offline — will sync |
