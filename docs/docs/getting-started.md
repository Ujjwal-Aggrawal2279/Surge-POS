---
id: getting-started
title: Getting Started
sidebar_position: 1
---

# Getting Started

Surge POS runs on ERPNext v15. Open `/surge` in any browser on your local network.

## Setup order

1. [Install](installation) the app
2. [Configure](configuration) a POS Profile
3. [Add cashiers](cashier-setup) and assign PINs
4. [Open a session](session-security) — Frappe login → profile → PIN
5. [Make a sale](making-a-sale)

## How identity works

| Layer | What it is | Scope |
|---|---|---|
| Frappe session | Username + password login | Browser tab |
| POS Profile | Counter / outlet config | Per terminal |
| Cashier PIN | 4–8 digit code per cashier | Per shift |

One Frappe session per terminal. Multiple cashiers share it by locking and unlocking with their PIN — no full re-login required.
