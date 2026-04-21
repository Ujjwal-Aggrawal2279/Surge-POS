---
id: installation
title: Installation
sidebar_position: 2
---

# Installation

```bash
bench get-app https://github.com/Ujjwal-Aggrawal2279/Surge-POS.git --branch develop
bench install-app surge
bench build --app surge
```

Open `https://<your-site>/surge`.

**Dev setup:**
```bash
cd apps/surge/web && npm install && npm run dev
```
Keep `bench start` running alongside.

**Upgrade:**
```bash
git pull origin develop && bench migrate && bench build --app surge
```
