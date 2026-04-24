---
id: troubleshooting
title: Troubleshooting
sidebar_position: 12
---

# Troubleshooting

| Symptom | Fix |
|---|---|
| Blank screen on `/surge` | Run `bench build --app surge`, hard-refresh browser |
| No cashiers on PIN screen | Add user to POS Profile → Applicable For Users; set Status = Active |
| PIN auto-generated but unknown | Manager resets via `surge.api.auth.set_pin` from Desk console |
| "Account locked" on PIN screen | Wait 5 min, or Manager calls `override_lockout` |
| Items not showing in grid | Check item has a price in the active Price List; check **Is Sales Item** |
| Items showing as "Out" | Stock is 0 in the profile's warehouse — create a Material Receipt |
| Barcode scan not adding item | Confirm barcode is in `tabItem Barcode` child table; check case (case-insensitive match) |
| Approvals bell not showing badge | Hard-refresh manager's tab; badge loads on mount and updates via realtime |
| "Network error" on PIN approval | Ensure the site is on HTTPS in production; HTTP disables `crypto.subtle` in some browsers |
| Manager approval modal stuck "Waiting" | Request is active for 30 min — manager can still approve; cashier can cancel and resend |
| Offline invoice not syncing | Check `bench logs`; check Surge Write Queue in Desk for status and error detail |
| Session expired overlay appears | Re-authenticate — cart in the current tab is preserved |
| Idle lock fires unexpectedly | Default timeout is 15 min; dismissible with "I'm here" button 15 s before lock |

For unresolved issues, open a [GitHub issue](https://github.com/Ujjwal-Aggrawal2279/Surge-POS/issues) with your Surge and ERPNext versions plus the browser console output.
