---
id: reports
title: Reports
sidebar_position: 10
---

# Reports

Surge POS submits standard ERPNext **POS Invoices**, so all ERPNext reports work out of the box.

Useful reports: **POS Report**, **Sales Register**, **Item-wise Sales Register**, **POS Closing Entry**.

Each invoice stores the cashier employee — filter by `cashier` in Sales Register to see per-cashier totals.

## Z-report (shift close)

The Z-report is generated automatically on shift close. It contains:

| Field | Description |
|---|---|
| Net sales | Total invoice value for the shift |
| Net returns | Total credit notes raised during shift |
| Payment mode breakdown | Collected amount per payment mode (Cash, UPI, Card, etc.) |
| Cash discrepancy | Actual counted cash − expected cash from invoices |

Access past Z-reports from ERPNext → Surge POS Closing Entry.

## Discount audit trail

Every invoice with a supervisor/manager discount override stores:
- `override_approved_by` — the approving user
- `override_approved_at` — UTC timestamp of approval
- `override_reason` — reason text supplied at approval time

These fields are read-only and permission-levelled (System Manager only). Filter Sales Register by `override_approved_by` to audit all non-standard discounts.
