---
id: troubleshooting
title: Troubleshooting
sidebar_position: 12
---

# Troubleshooting

| Symptom | Fix |
|---|---|
| Blank screen | Run `bench build --app surge`, clear browser cache |
| No cashiers on picker | Add a Cashier record linked to the active POS Profile |
| Items not showing | Check price in active Price List; check Is Sales Item |
| Payment error | Check `bench logs`; verify POS Profile tax + account config |
| Sync icon stuck | Refresh the page; invoice will retry when online |
| PIN screen after idle | Expected — enter PIN to resume (default idle timeout: 15 min) |

For unresolved issues, open a [GitHub issue](https://github.com/Ujjwal-Aggrawal2279/Surge-POS/issues) with your Surge and ERPNext versions plus the browser console output.
