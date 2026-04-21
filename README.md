# Surge POS

> High-performance Point of Sale for ERPNext — built for Indian liquor retail, general merchandise, and quick-service outlets.

[![CI](https://github.com/Ujjwal-Aggrawal2279/Surge-POS/actions/workflows/ci.yml/badge.svg)](https://github.com/Ujjwal-Aggrawal2279/Surge-POS/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

Surge POS is a Frappe app that replaces the default ERPNext POS with a fast, touch-friendly terminal designed for high-volume retail. It ships as a standard Frappe app — install it on any ERPNext v15 bench in minutes.

**Key highlights**

- Two-layer identity: Frappe session per terminal + PIN-based cashier switch, no re-login between shifts
- Offline-first: sales queue to IndexedDB when connectivity drops, auto-syncs on reconnect
- Delta-sync item catalog: handles 5,000+ SKUs without full-page reloads
- India compliance hooks: excise permit capture, state-wise MRP enforcement, TPT/L-1 licence tracking (plugin)
- Extensible: vertical modules (liquor, pharmacy, fuel) plug in without forking the core

---

## Requirements

| Dependency | Version |
|---|---|
| Frappe / ERPNext | ≥ 15.0 |
| Python | ≥ 3.10 |
| Node.js | ≥ 18 |

---

## Installation

```bash
# From your bench root
bench get-app https://github.com/Ujjwal-Aggrawal2279/Surge-POS.git --branch develop
bench install-app surge

# Build frontend assets
bench build --app surge
```

### Development setup

```bash
cd apps/surge

# Python tools
pip install -e ".[dev]"
pre-commit install        # ruff + eslint + prettier on every commit

# Frontend
cd web
npm install
npm run dev               # Vite dev server with HMR
```

---

## Configuration

1. **Create a POS Profile** in ERPNext (`POS Profile` doctype) and assign it to the desired warehouse and price list.
2. **Assign cashiers**: open the Surge POS Settings and link employee records to PIN codes.
3. **Navigate** to `/surge` — the terminal picks up the active POS Profile automatically.

Full walkthrough → [docs/](docs/)

---

## Project Structure

```
apps/surge/
├── surge/                  # Frappe app backend
│   ├── api/                # REST endpoints (items, invoices, sessions)
│   ├── surge_pos/          # DocTypes (Cashier, POS Profile extension)
│   ├── www/surge/          # Frappe page that hosts the SPA
│   └── public/             # Compiled assets + static images
├── web/                    # Vite + React frontend
│   └── src/
│       ├── components/pos/ # ItemGrid, Cart, PaymentDialog, …
│       ├── pages/          # CashierScreen, SellScreen, LoginScreen
│       ├── stores/         # Zustand stores (cart, session)
│       └── hooks/          # TanStack Query hooks
├── .github/
│   ├── workflows/          # CI + release pipelines
│   └── ISSUE_TEMPLATE/
├── docs/                   # Docusaurus user guide
└── pyproject.toml
```

---

## Contributing

Pull requests are welcome. For significant changes please open an issue first.

```bash
# Run frontend checks
cd web && npm run lint && npm run typecheck

# Run Python checks
ruff check . && ruff format --check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions and commit message format.

---

## Roadmap

- [ ] Offline sync queue with conflict resolution
- [ ] WhatsApp receipt delivery
- [ ] UPI QR auto-verify via payment gateway webhook
- [ ] Anomaly detection on cashier voids / discounts
- [ ] Liquor compliance plugin (excise permits, TPT integration)

---

## License

[MIT](LICENSE) © 2026 Ujjwal Aggrawal
