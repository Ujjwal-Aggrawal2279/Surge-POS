# Surge POS — Full System Architecture

> **Stack:** React 19 · Frappe Python · orjson · msgspec · MariaDB · Redis · ERPNext v15 · India Compliance
> **Deployment:** Frappe Cloud (single app install) or self-hosted bench
> **Principle:** Every decision below is final. No open "it depends" items.

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     POS Terminal (Browser PWA)                   │
│                                                                  │
│   React 19 + Vite + TypeScript                                   │
│   Zustand (local state) · TanStack Query (server state)          │
│   shadcn/ui + Tailwind CSS v4                                    │
│   libsql (SQLite WASM) — offline store                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTPS / Frappe socketio
┌────────────────────────▼─────────────────────────────────────────┐
│               Surge — Frappe App (Python)                        │
│                                                                  │
│   surge/api/          — whitelisted API endpoints                │
│   surge/jobs/         — RQ background jobs (write queue flush)   │
│   surge/public/dist/  — built React PWA (served by Nginx)        │
│                                                                  │
│   orjson   — 10x faster JSON serialization                       │
│   msgspec  — typed request/response validation                   │
│   Redis    — hot cache (items, prices, stock)                    │
│   RQ       — background write queue processor                    │
└──────────┬──────────────────────────┬────────────────────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼──────────────────────────┐
│  MariaDB pos_sync   │   │  MariaDB _site_db (ERPNext)          │
│                     │   │                                      │
│  • write_queue      │   │  • Sales Invoice, Stock, Accounts   │
│  • sync_watermarks  │   │  • India Compliance (GST/e-Invoice) │
│  • audit_log        │   │  • Item, Customer, POS Profile      │
│  • hardware_events  │   │  • Opening/Closing Shift            │
└──────────────────────┘   └──────────────────────────────────────┘
```

---

## 2. Tech Stack — Final Decisions

### 2.1 Frontend (unchanged)

| Concern | Choice |
|---------|--------|
| Framework | **React 19** |
| Build tool | **Vite 6** |
| Language | **TypeScript 5.5 (strict)** |
| Styling | **Tailwind CSS v4 + shadcn/ui** |
| State (local) | **Zustand** |
| State (server) | **TanStack Query v5** |
| Offline DB | **libsql (SQLite WASM)** |
| Routing | **TanStack Router** |
| Forms | **React Hook Form + Zod** |
| Icons | **Lucide React** |
| Testing | **Vitest + Testing Library + Playwright** |

### 2.2 Backend (Frappe Python App)

| Concern | Choice | Reason |
|---------|--------|--------|
| Framework | **Frappe v15** | Native ERPNext integration, Frappe Cloud compatible |
| Language | **Python 3.11+** | Frappe requirement |
| JSON | **orjson** | Rust-core, 10x faster than stdlib json, drop-in replacement |
| Validation | **msgspec** | Faster than Pydantic, Rust-core encoder/decoder |
| HTTP client | **httpx** | Async-capable, used for Pine Labs / external API calls |
| Background jobs | **RQ** (Frappe built-in) | Write queue flush, sync engine |
| WebSocket | **frappe.publish_realtime** | Built-in socketio, no extra infra |
| Cache | **Redis** (Frappe built-in) | Hot item catalog, prices, stock snapshot |
| Auth | **Frappe session** | Built-in, Frappe Cloud compatible |

### 2.3 Data Layer

| Store | Engine | Purpose |
|-------|--------|---------|
| ERPNext data | **MariaDB** `_site_db` | Invoices, stock, items, customers — ERPNext owned |
| Sync metadata | **MariaDB** `pos_sync` db | Write queue, watermarks, audit log |
| Hot cache | **Redis** | Item catalog snapshot, price list, stock levels |
| Offline store | **libsql (SQLite WASM)** | Terminal-local data, survives full disconnect |

---

## 3. Frappe App Structure

```
surge/                              ← git root (monorepo)
├── surge/                          ← Frappe app (pip installable)
│   ├── surge/                      ← Python module
│   │   ├── __init__.py
│   │   ├── hooks.py                ← Frappe event hooks
│   │   ├── modules.txt
│   │   ├── api/                    ← Whitelisted API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── items.py
│   │   │   ├── stock.py
│   │   │   ├── customers.py
│   │   │   ├── invoices.py
│   │   │   ├── profile.py
│   │   │   ├── shift.py
│   │   │   └── sync.py
│   │   ├── jobs/                   ← RQ background jobs
│   │   │   ├── __init__.py
│   │   │   └── sync_engine.py
│   │   ├── utils/                  ← Shared utilities
│   │   │   ├── __init__.py
│   │   │   ├── cache.py            ← Redis helpers
│   │   │   ├── json.py             ← orjson wrappers
│   │   │   └── response.py         ← Typed response builders (msgspec)
│   │   └── www/
│   │       └── surge.html          ← App shell (serves React PWA)
│   ├── public/
│   │   └── dist/                   ← Built React assets (Vite output)
│   ├── setup.py
│   ├── requirements.txt
│   └── pyproject.toml
└── frontend/                       ← React app
    ├── src/
    ├── package.json
    └── vite.config.ts
```

---

## 4. Python API Design

All endpoints use `@frappe.whitelist()`. Responses serialized with **orjson** for maximum throughput.

### 4.1 Items Sync
```
GET /api/method/surge.surge.api.items.get_items
  ?profile=LV+Main+Counter&since=2024-01-01T00:00:00Z&limit=500
→ { items: [...], watermark: "2024-06-01T12:00:00Z", count: 423 }
```

### 4.2 Stock Sync
```
GET /api/method/surge.surge.api.stock.get_stock
  ?warehouse=Stores+-+LV&since=...
→ { stock: [...], watermark: "...", count: 89 }
```

### 4.3 Create Invoice
```
POST /api/method/surge.surge.api.invoices.create_invoice
  { client_request_id, pos_profile, customer, items, payments, offline }
→ { invoice_name, status: "submitted"|"queued", grand_total_paise }
```

### 4.4 Sync Queue Status
```
GET /api/method/surge.surge.api.sync.queue_status
→ { pending: 0, failed: 0, done: 142 }
```

---

## 5. Write Queue Flow

```
Online:   create_invoice → Frappe submit_invoice → docstatus=1 → stock deducted ✅
Offline:  create_invoice → write_queue (MariaDB) → status=pending → return "queued"
          ↓ RQ job fires every 10s
          claim_pending → submit_invoice → mark_done → frappe.publish_realtime
```

Failed items (5 retries exhausted) → visible in Surge UI dead-letter panel.

---

## 6. Performance Optimisations

### orjson response wrapper
```python
import orjson
from frappe import Response

def surge_response(data: dict) -> Response:
    return Response(
        orjson.dumps(data),
        status=200,
        mimetype="application/json"
    )
```

### Redis item cache (5-min TTL)
```python
import redis, orjson

def get_cached_items(profile: str):
    key = f"surge:items:{profile}"
    cached = frappe.cache().get_value(key)
    if cached:
        return orjson.loads(cached)
    items = fetch_items_from_db(profile)
    frappe.cache().set_value(key, orjson.dumps(items), expires_in_sec=300)
    return items
```

### msgspec typed validation
```python
import msgspec

class InvoiceItem(msgspec.Struct):
    item_code: str
    qty: float
    rate_paise: int
    discount_paise: int = 0
    warehouse: str | None = None

class CreateInvoiceRequest(msgspec.Struct):
    client_request_id: str
    pos_profile: str
    customer: str
    items: list[InvoiceItem]
    payments: list[PaymentItem]
    offline: bool = False

decoder = msgspec.json.Decoder(CreateInvoiceRequest)
```

---

## 7. Frappe Cloud Deployment

```bash
# Install on any ERPNext instance
bench get-app https://github.com/yourusername/surge
bench --site mysite.local install-app surge

# Frappe Cloud — one-click via marketplace
# or via custom app install
```

React frontend is built and committed to `surge/public/dist/` — served by Frappe/Nginx with no additional server needed.

---

## 8. Development Milestones

| Phase | Deliverable | Duration |
|-------|-------------|----------|
| **P0 — Foundation** | Frappe app scaffolded, item/stock/customer API working | 1 week |
| **P1 — Sell Flow** | React UI: cart, cash payment, invoice submitted to ERPNext | 2 weeks |
| **P2 — Offline** | libsql sync, write queue, offline sell, auto-flush on reconnect | 2 weeks |
| **P3 — Payments** | Pine Labs webhook bridge, UPI QR (Razorpay) | 2 weeks |
| **P4 — Shift Mgmt** | Opening/closing shift, Z-report, cash register | 1 week |
| **P5 — India** | GST invoice print with IRN QR, GSTIN on B2B invoices | 1 week |
| **P6 — Hardening** | Dead-letter UI, perf profiling, E2E tests, Frappe Cloud publish | 2 weeks |

**Total: ~11 weeks to Frappe Cloud ready v1.**

---

*Architecture version: 2.0 (Option A — Frappe App) — April 2026*
