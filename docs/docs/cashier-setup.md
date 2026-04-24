---
id: cashier-setup
title: Cashier Setup
sidebar_position: 4
---

# Cashier Setup

## Access levels

| Level | Discount limit | Can approve remotely | Can set PINs |
|---|---|---|---|
| Cashier | Up to 5% | No | No |
| Supervisor | Up to configured limit | Yes | No |
| Manager | Up to 100% | Yes | Yes |

## Adding cashiers to a POS Profile

1. Open the POS Profile in ERPNext Desk.
2. Under **Applicable For Users**, add the Frappe user.
3. Set **Access Level** (Cashier / Supervisor / Manager).
4. **PIN is auto-generated** on Save — a unique 4-digit PIN is assigned if none exists.
5. To change a PIN: a Manager calls `surge.api.auth.set_pin` from the Surge settings panel or Desk console.

## Cashier states on the PIN screen

| Badge | Meaning |
|---|---|
| *(no badge)* | Ready — enter PIN |
| Locked | 3 wrong PINs — 5-min cooldown |
| No PIN | PIN not yet configured — contact Manager |

## Shift handover

**Lock** (not logout) for cashier switches — the Frappe session stays open, the next cashier just enters their PIN. Use **Logout** only when closing the terminal for the day.
