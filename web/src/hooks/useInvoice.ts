import { useMutation, useQueryClient } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { enqueue, dequeue, getAllPending } from "@/lib/offline-queue";
import { uuidv7 } from "@/lib/utils";
import type { CreateInvoiceRequest, CartItem, PaymentEntry } from "@/types/pos";

interface InvoiceResult {
  invoice_name: string | null;
  client_request_id: string;
  status: "submitted" | "queued";
  grand_total_paise: number;
}

interface SubmitArgs {
  items: CartItem[];
  payments: PaymentEntry[];
  customer: string;
  pos_profile: string;
  approval_token?: string | null;
}

export function useSubmitInvoice() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({ items, payments, customer, pos_profile, approval_token }: SubmitArgs) => {
      const req: CreateInvoiceRequest = {
        client_request_id: uuidv7(),
        pos_profile,
        customer,
        items: items.map((i) => ({
          item_code: i.item_code,
          qty: i.qty,
          rate_paise: i.rate_paise,
          discount_paise: i.discount_paise,
          warehouse: i.warehouse ?? null,
        })),
        payments,
        offline: !navigator.onLine,
        approval_token: approval_token ?? null,
      };

      const grand_total_paise = payments.reduce((s, p) => s + p.amount_paise, 0);

      // Offline path — enqueue immediately, no server call
      if (!navigator.onLine) {
        await _safeEnqueue(req);
        return {
          ...req,
          invoice_name: null,
          status: "queued" as const,
          grand_total_paise,
        };
      }

      // Online path
      try {
        const result = await post<InvoiceResult>(
          "surge.api.invoices.create_invoice",
          req,
        );

        if (result.status === "submitted") {
          // Server confirmed submission — remove from local queue if it was queued
          await dequeue(req.client_request_id).catch(() => undefined);
        } else {
          // Server queued it (e.g. ERPNext backlog) — mirror locally
          await _safeEnqueue(req);
        }

        return result;

      } catch {
        // Network failure or server error — enqueue locally, never lose a sale
        await _safeEnqueue(req);
        return {
          ...req,
          invoice_name: null,
          status: "queued" as const,
          grand_total_paise,
        };
      }
    },

    onSuccess: () => {
      // Invalidate stock so the UI reflects deducted qty immediately
      qc.invalidateQueries({ queryKey: ["stock"] });
    },
  });
}

/**
 * Enqueue with duplicate guard.
 *
 * Worst case: the app enqueues, crashes, restarts, and tries to enqueue again.
 * IndexedDB put() is idempotent on the keyPath (client_request_id) — it upserts,
 * so duplicate enqueues are safe. This wrapper is defensive documentation.
 */
async function _safeEnqueue(req: CreateInvoiceRequest): Promise<void> {
  try {
    // Check if already in the local queue (e.g. page was refreshed mid-transaction)
    const pending = await getAllPending();
    const alreadyQueued = pending.some(
      (r) => r.client_request_id === req.client_request_id,
    );
    if (!alreadyQueued) {
      await enqueue(req);
    }
  } catch (err) {
    // IndexedDB failure (private browsing, storage quota) — log but don't crash
    // The server may still have the invoice if the POST succeeded
    console.error("Surge: failed to write to offline queue:", err);
  }
}
