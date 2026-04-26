---
id: pos-profile
title: POS Profile
sidebar_position: 8
---

# POS Profile

The ERPNext POS Profile links warehouse, price list, taxes, payment methods, and allowed users to a terminal. One profile per counter is the standard setup. Multiple profiles on the same site are supported (e.g. per shift or per outlet).

## Key fields

| Field | Description |
|---|---|
| **Warehouse** | Default stock warehouse for all items at this terminal |
| **Selling Price List** | MRP or custom price list applied to every sale |
| **Company** | ERPNext company for GL entries |
| **Currency** | Transaction currency (INR for India) |
| **Write Off Account** | Account used for sub-₹1 GST rounding adjustments |
| **Write Off Limit** | Maximum rounding gap (in ₹) that is written off automatically. Set to `1` for standard GST rounding. If unset or `0`, exact payment is required — any shortfall fails the invoice. |
| **Allow Discount Change** | Master switch — must be enabled before any discount can be applied |
| **Allow Partial Payment** | If disabled (default), the full invoice amount must be collected before checkout |

## Surge-specific fields

| Field | Description |
|---|---|
| **Cashier Discount Limit (%)** | Maximum discount a Cashier can apply without approval. Default 5%. |
| **Supervisor Discount Limit (%)** | Maximum discount a Supervisor can approve. Default 15%. |
| **Manager Discount Limit (%)** | Maximum discount a Manager can approve. Default 100%. |

## Payment methods

Add each mode of payment (Cash, UPI, Card, etc.) under **Applicable Payment Methods**. Each mode must have a default account configured for the company in ERPNext → Mode of Payment. Modes without an account will fail GL entry creation at invoice submit time.

## Users

Add each cashier under **Applicable For Users**. Set **Access Level** (Cashier / Supervisor / Manager) and **Status** (Active / Inactive). Only Active users can log in and open a shift. A PIN is auto-generated on Save.

## Disabled profiles

If a profile is set to **Disabled**, all API access (login, session open, invoice submission) is rejected with a permission error.
