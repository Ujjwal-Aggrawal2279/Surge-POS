# Surge POS

High-performance POS for ERPNext · Built with React 19 + Rust (Axum) · India-first

## Structure

```
surge/
├── api/    Rust middleware (Axum) — runs on port 7700
└── web/    React 19 frontend (Vite) — runs on port 5173
```

## Quick start

```bash
# API
cd api && cargo run

# Web
cd web && pnpm dev
```
