# Surge POS — Complete Feature List
*165 features across 15 categories*

---

## 1. SHIFT MANAGEMENT
- Open shift with declared opening float per payment mode
- Multiple cashiers per shift (multi-counter stores)
- Multiple shifts per day (morning / afternoon / night)
- Cash in (deposit) during shift with reason
- Cash out (expense) during shift with reason
- Manager approval for cash withdrawals above threshold
- Blind cash close (cashier counts first, sees expected after)
- Z-report — expected vs actual per payment mode with discrepancy
- X-report — mid-shift snapshot without closing
- Shift-wise sales summary (invoices, returns, net total, taxes)
- Shift discrepancy reason recording (for audit)
- Cashier handover (mid-shift takeover)
- Draft invoices auto-cleanup on shift close
- Shift-level audit trail (all actions timestamped)

## 2. INVOICE / BILLING
- Fast checkout with barcode scan to add items
- Item search by name, code, barcode
- Manual quantity entry and edit
- Item variants selection (size, colour, weight)
- Multiple UOM per item (e.g., kg / piece / dozen)
- Item-level discount (% or flat amount)
- Bill-level additional discount
- Discount limit enforcement per cashier role
- Manager override PIN for above-limit discounts
- Note / remark on invoice line
- Hold / park order and resume later
- Recall held orders list
- Draft invoice save and reload
- Delete draft invoice (with manager confirmation)
- Reprint last invoice
- Reprint any past invoice
- Invoice preview before print
- Digital invoice (WhatsApp / SMS / email)
- Sequential tamper-proof invoice numbering
- Custom invoice / receipt format per POS profile
- Multi-page invoice support (large carts)
- Currency display with formatting

## 3. PAYMENTS
- Cash payment with auto change calculation
- UPI dynamic QR code display (amount pre-filled)
- UPI payment status polling + auto-confirm
- Card terminal integration (Pine Labs, Ingenico, Verifone — auto push amount)
- Split payment across multiple modes in one bill
- Write-off small balance (rounding)
- Payment rounding to nearest ₹1 / ₹5
- Denomination-wise cash received entry
- Credit sale (on-account for known customer)
- Customer advance / store credit redemption
- Gift card issuance and redemption
- Wallet payments (Paytm, PhonePe, Google Pay)
- Partial payment with balance due
- Refund to original payment method
- Refund as store credit / credit note
- Cash drawer kick via ESC/POS RJ11
- Payment entry idempotency (retry-safe)
- Multi-currency with live exchange rate

## 4. INVENTORY / STOCK
- Real-time stock deduction on invoice submit
- Stock display on item grid (available qty)
- Out-of-stock item visual indicator and soft block
- Low-stock alert (configurable threshold per item)
- Batch / lot number tracking
- Serial number tracking
- Expiry date tracking with near-expiry alerts
- FIFO / FEFO stock picking enforcement
- Item variants (colour, size, weight, etc.)
- Multiple UOM per item with conversion
- Case-break / pack-break (buy in cases, sell in pieces)
- Weighing scale integration (USB / serial)
- Barcode label printing from POS
- Physical stock count / stocktake from POS
- Stock transfer between warehouses from POS
- Dead stock / slow-mover identification
- Reorder point trigger and purchase suggestion
- Supplier-linked items for purchase returns

## 5. CUSTOMERS
- Customer search by name / phone / email / tax ID
- Quick customer create from POS (name + phone)
- Customer edit from POS
- Walk-in / anonymous customer default
- Customer purchase history at POS
- Customer running balance (AR / credit)
- Credit limit enforcement with override
- Digital Khata (running tab for regular customers)
- Customer segmentation (VIP / Regular / Walk-in)
- Blacklist / blocked customer flag with reason
- Customer-facing pole display / second screen
- WhatsApp receipt on sale
- SMS receipt on sale
- Email receipt on sale
- Customer loyalty points accrual on purchase
- Loyalty points redemption at checkout
- Tiered loyalty program (Silver / Gold / Platinum)

## 6. PROMOTIONS & OFFERS
- Item-level promotional pricing (rate / % / flat)
- Bill-level discount scheme
- Buy X Get Y (BOGO)
- Buy X Get Y Free (Give Product)
- Mix-and-match pricing (any 3 for ₹X)
- Min quantity / min amount threshold offers
- Brand / item group / item code scoped offers
- Auto-apply offers (no cashier action needed)
- Coupon code entry at checkout
- Coupon validity (date range + max usage)
- One-use-per-customer coupon enforcement
- Time-based offers (happy hour, evening rush)
- Promotional scheme validity enforcement
- Promo usage limit (max redemptions)
- Referral code tracking
- Vendor-funded promotion tagging
- Promotion utilisation report (cost vs revenue)
- Stackable promotions (configurable)
- Loyalty points as offer reward

## 7. RETURNS & REFUNDS
- Full return against original invoice
- Partial return (select specific items and qty)
- Return without original invoice (walk-in return)
- Return reason capture (mandatory)
- Return validity window enforcement (configurable days)
- Manager approval for returns above ₹ threshold
- Return to shelf vs damaged / write-off bin
- Return stock auto-posted back to warehouse
- Refund to original payment method
- Refund as store credit / advance payment
- Supplier / vendor return from POS
- Return analysis report (volume, reasons, cashier)

## 8. HARDWARE
- Thermal receipt printer — 58mm and 80mm ESC/POS
- Network receipt printer (IP-based)
- Bluetooth receipt printer
- USB barcode scanner (HID plug-and-play)
- Bluetooth barcode scanner
- 2D / QR code scanner (for UPI, HSN lookup)
- Cash drawer kick (via printer RJ11 port)
- Weighing scale (USB / RS-232 serial)
- Customer-facing pole display (VFD / LCD / second screen)
- Card terminal (Pine Labs, Ingenico, Verifone)
- UPI QR display device (BharatQR terminal)
- Label printer (Zebra / TSC for price labels)
- ID / document scanner (for age or customer verification)
- Tablet / touch-screen optimised layout
- Android tablet support
- iPad / iOS support
- Keyboard shortcut support for speed checkout
- Offline-capable kiosk mode (PWA installable)

## 9. INDIA COMPLIANCE
- GST invoice with CGST / SGST / IGST / UTGST split
- HSN / SAC code per item line on invoice
- e-Invoice — IRN generation + QR embed (via india-compliance)
- e-Waybill generation for inter-state transport
- GSTR-1 compatible invoice data
- GSTR-3B report feeds
- Composite tax schemes (cascading tax support)
- Tax inclusive / exclusive mode per POS profile
- UPI mandate compliance
- State-specific invoice format (configurable template)
- Invoice with GSTIN of buyer for B2B sales
- Reverse charge flag on invoice

## 10. REPORTING & ANALYTICS
- Daily sales summary (by cashier, by store, by shift)
- Brand / category / SKU-wise sales report
- Payment-mode-wise collection report
- Shift closing Z-report
- Hourly sales heatmap (peak hour analysis)
- Top 20 / bottom 20 SKUs by revenue and qty
- Gross margin by item / category / brand
- Cashier performance report (sales, discounts, returns, voids)
- Discount utilisation report
- Returns / voids analysis (fraud detection)
- Stock ageing / expiry report
- Customer purchase frequency report
- Loyalty points report
- Promotion / offer P&L report
- Comparison vs prior period (day / week / month)
- Owner mobile live dashboard (real-time remote view)
- Scheduled report delivery (WhatsApp / email / SMS)
- Export to Excel / CSV / PDF

## 11. OFFLINE & SYNC
- Full offline billing (no internet required)
- IndexedDB local cache (items, prices, stock, customers)
- Service Worker for full asset caching (PWA)
- Background sync write queue (exponential backoff + jitter)
- Circuit breaker (pause sync if server consistently down)
- Multi-terminal optimistic stock lock (prevent overselling)
- Conflict resolution with manager review UI (dead-letter panel)
- Sync status indicator in UI (online / offline / syncing / failed)
- Delta sync — only changed records after watermark
- Schema version check — full resync on app update
- Offline returns (queued, synced on reconnect)
- Offline stock counter (local deduction while offline)
- Queue status dashboard for operators

## 12. SECURITY & ACCESS CONTROL
- Role-based access — Cashier / Manager / Owner / Admin
- PIN / password login per cashier at terminal
- Manager override PIN for sensitive actions
- Discount limit per cashier role (max % allowed)
- Void / cancel requires manager approval
- Price override requires manager approval
- Return above threshold requires manager approval
- Cash drawer open event log
- Failed login attempt lockout
- Session timeout / auto-lock (configurable idle time)
- End-of-day tamper-proof audit log
- All edits / cancellations / voids logged (who, what, when)
- Owner read-only remote access
- Transaction modification history per invoice
- Employee-wise void and discount report

## 13. CONFIGURATION & SETUP
- Multiple POS profiles per company
- POS profile per cashier / terminal / warehouse
- Configurable payment modes per profile
- Configurable item groups visible per profile
- Configurable customer groups per profile
- Warehouse assignment per POS profile
- Price list per POS profile
- Tax template per POS profile
- Custom fields on invoice from POS profile
- Multi-company support
- Multi-store / multi-location support
- Multi-currency per terminal
- Multilingual UI (Hindi + regional languages)
- Dark mode / light mode toggle
- Custom receipt logo and footer text
- Keyboard shortcut customisation

## 14. INTEGRATIONS
- ERPNext (native — Sales Invoice, POS Invoice, Stock, GL)
- India Compliance app (GST, e-Invoice, e-Waybill)
- Razorpay (UPI QR + payment confirmation webhook)
- Pine Labs (card terminal API)
- Stripe (international card payments)
- WhatsApp Business API (receipts, reports)
- SMS gateway (MSG91, Fast2SMS)
- Email (SMTP via Frappe)
- Loyalty program (ERPNext native)
- CRM / customer data sync
- Purchase module (supplier returns, reorder)
- Accounts (GL entries, payment reconciliation)
- Cost centre tracking per POS profile

## 15. VERTICAL MODULES (optional plugins)
- **Liquor Retail** — MRP enforcement, IMFL/CL registers, excise reports, age verification, state parcha formats, sale-hour blocking
- **Restaurant / QSR** — Table management, KOT (kitchen order ticket), course-wise serving, modifiers, split bill by person
- **Pharmacy** — Schedule H drug flags, prescription upload, batch + expiry mandatory, drug interaction alert
- **Grocery / Supermarket** — Weighing scale mandatory, PLU codes, produce tare weight
- **Apparel** — Size/colour matrix, season tagging, alteration orders
- **Electronics** — Serial number mandatory, warranty registration, IMEI tracking
