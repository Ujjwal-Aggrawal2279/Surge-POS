---
id: installation
title: Installation
sidebar_position: 2
---

# Installation

## Self-hosted (bench)

```bash
bench get-app https://github.com/Ujjwal-Aggrawal2279/Surge-POS.git --branch main
bench --site <your-site> install-app surge
bench --site <your-site> migrate
bench build --app surge
```

Open `https://<your-site>/surge`.

The repository ships pre-built frontend assets in `surge/public/dist/` — `bench build` copies them to the site's assets folder. No separate Node/pnpm step is required on the server.

## Frappe Cloud

1. Add the Surge POS app via **Frappe Cloud → Apps → Add App** (GitHub URL, `main` branch).
2. Deploy the site — Frappe Cloud runs `bench build --app surge` automatically, which copies the committed assets.
3. Open `https://<site>.frappe.cloud/surge`.

## Dev setup

```bash
cd apps/surge/web
pnpm install
pnpm dev          # Vite dev server at localhost:5173
```

Keep `bench start` running alongside.

## Upgrade

```bash
cd apps/surge
git pull origin main
bench --site <your-site> migrate
bench build --app surge
```

If you changed any frontend source files locally, rebuild before upgrading:

```bash
cd apps/surge/web && pnpm build
# then commit surge/public/dist/ + surge/www/surge.html
git add ../surge/public/dist/ ../surge/www/surge.html
git commit -m "chore: rebuild frontend"
```

## Frontend build rule

**Always commit `surge/public/dist/` and `surge/www/surge.html` together after any frontend change.**

Frappe Cloud and self-hosted `bench build` both copy pre-built assets — they do not run Vite on the server. If the committed dist is stale, the HTML will reference chunk hashes that do not exist, causing a white screen. The CI pipeline enforces this with a `git diff --exit-code` check on every push.
