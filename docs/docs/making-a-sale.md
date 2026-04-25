---
id: making-a-sale
title: Making a Sale
sidebar_position: 7
---

# Making a Sale

## Adding items

| Method | How |
|---|---|
| Click card | Tap any item in the grid — adds 1 qty |
| Barcode scan | Focus search box → scan (USB / Bluetooth wedge scanner) → item auto-added |
| Item code | Type exact item code → Enter → item auto-added |
| Partial search | Type partial name or code → grid filters → click the card |

**Barcode matching is case-insensitive.** Scanning `lv2024006` matches barcode `LV2024006`.

**Auto-add on Enter** only fires on an exact match (one item). Partial matches just filter the grid — no item is added automatically.

## Adjusting quantity

- **+** / **−** buttons on the cart row.
- Setting qty to 0 removes the line.

## Grid vs List view

The toggle in the top-right of the product area (next to the search box) switches between two layouts:

| View | Best for |
|---|---|
| **Grid** (default) | Browsing by image/icon — quick visual recognition |
| **List** | High-SKU screens or scanning by name — more items visible at once |

Your choice persists across page refreshes and sessions (stored locally in the browser). Switch back at any time with the same toggle.

## Filters

Category tabs filter the item grid. **View All Categories** resets to show everything.

## Customer

Defaults to Walk-in Customer. Click **Add Customer** to link a named ERPNext Customer to the invoice.

## Discounts

Click **Discount** in the cart action bar.

- Within your access-level limit → applied immediately, no approval needed.
- Above your limit → triggers the [Manager Approval](manager-approvals) flow.

## Checkout

Click the green **Grand Total** button (or **Payment** in the action bar) to open the payment dialog.
