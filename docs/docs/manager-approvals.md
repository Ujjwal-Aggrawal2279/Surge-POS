---
id: manager-approvals
title: Manager Approvals
sidebar_position: 6
---

# Manager Approvals

Discounts beyond a cashier's limit require approval from a Supervisor or Manager — who can approve from their own screen, remotely.

## Discount limits

| Role | Auto-applied (no approval) | Requires approval |
|---|---|---|
| Cashier | ≤ 5% | > 5% |
| Supervisor | ≤ configured limit | Above limit |
| Manager | ≤ 100% | — |

## Remote approval flow

### Cashier side

1. Add item → click **Discount** → enter percentage above your limit.
2. **Request Approval** button appears (amber).
3. Select a Manager or Supervisor from the list → **Send Approval Request**.
4. Modal transitions to spinner: "Waiting for [Name]" with a 3-minute countdown.
5. When approved: "Approved by [Name]" — discount applies to cart automatically.
6. When denied: "Request Denied" — **Try again** resets the flow.

### Manager / Supervisor side

1. Bell icon in the navbar shows a badge with pending count.
2. Click **Approvals** → see list of pending requests.
3. Click a request → **Review** → enter your PIN → **Approve** or **Deny**.

## States and edge cases

| Scenario | What happens |
|---|---|
| Manager approves within 3 min | Cashier screen resolves instantly (realtime) |
| Cashier's 3-min timer expires | Transitions to "Hasn't responded yet — request active 30 min" — poll continues every 3 s |
| Manager approves after 3-min display timer | Cashier screen resolves within 3 s (background poll catches it) |
| Cashier cancels request | Manager's badge clears immediately; Redis entry deleted |
| Page refresh while waiting | Modal restores to waiting state from session storage; poll resumes |
| Redis unavailable | Error: "Remote approval unavailable — ask manager to enter PIN on this screen"; same-screen PIN flow still works |

## Security

- Approval tokens are HMAC-signed (SHA-256) and one-time-use.
- A token consumed to create one invoice cannot be replayed for another.
- Tampered tokens are rejected with 403.
- Manager PIN is verified server-side; the hash never leaves the server.

## Notifications

- Managers receive a Frappe bell notification when a request is sent — visible even if they weren't logged into Surge at the time.
- The notification is marked read automatically on approve, deny, or cancel.
