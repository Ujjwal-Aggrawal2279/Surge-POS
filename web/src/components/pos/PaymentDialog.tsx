import { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Loader2, CheckCircle2, WifiOff } from "lucide-react";
import { useCartStore } from "@/stores/cart";
import { useSubmitInvoice } from "@/hooks/useInvoice";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";

const PAYMENT_MODES = ["Cash", "Card", "UPI"];

interface Props {
  open: boolean;
  onClose: () => void;
  posProfile: string;
  defaultMode?: string;
}

export function PaymentDialog({ open, onClose, posProfile, defaultMode }: Props) {
  const items = useCartStore((s) => s.items);
  const customer = useCartStore((s) => s.customer);
  const grandTotal = useCartStore((s) => s.grandTotalPaise());
  const clear = useCartStore((s) => s.clear);

  const [mode, setMode] = useState(defaultMode ?? "Cash");

  useEffect(() => {
    if (open) setMode(defaultMode ?? "Cash");
  }, [open, defaultMode]);
  const [result, setResult] = useState<{ invoiceName: string | null; status: string } | null>(null);

  const submit = useSubmitInvoice();

  async function handleCharge() {
    const res = await submit.mutateAsync({
      items,
      customer,
      pos_profile: posProfile,
      payments: [{ mode_of_payment: mode, amount_paise: grandTotal }],
    });
    setResult({ invoiceName: res.invoice_name, status: res.status });
  }

  function handleDone() {
    clear();
    setResult(null);
    onClose();
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && !submit.isPending && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-background p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-lg font-bold">Payment</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" disabled={submit.isPending}>
                <X className="h-4 w-4" />
              </Button>
            </Dialog.Close>
          </div>

          {result ? (
            <div className="flex flex-col items-center gap-4 py-6">
              {result.status === "submitted" ? (
                <CheckCircle2 className="h-16 w-16 text-green-500" />
              ) : (
                <WifiOff className="h-16 w-16 text-amber-500" />
              )}
              <p className="text-center font-semibold">
                {result.status === "submitted"
                  ? `Invoice ${result.invoiceName ?? ""} submitted`
                  : "Saved offline — will sync when connected"}
              </p>
              <p className="text-2xl font-bold">{formatCurrency(grandTotal)}</p>
              <Button size="lg" className="w-full" onClick={handleDone}>
                New Sale
              </Button>
            </div>
          ) : (
            <>
              <p className="mb-4 text-3xl font-bold text-center tabular-nums">
                {formatCurrency(grandTotal)}
              </p>

              <div className="mb-6 flex gap-2">
                {PAYMENT_MODES.map((m) => (
                  <button
                    type="button"
                    key={m}
                    onClick={() => setMode(m)}
                    className={`flex-1 rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                      mode === m
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input hover:bg-accent"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>

              <Button
                size="xl"
                className="w-full"
                disabled={submit.isPending}
                onClick={handleCharge}
              >
                {submit.isPending ? (
                  <><Loader2 className="h-5 w-5 animate-spin" /> Processing…</>
                ) : (
                  `Charge ${formatCurrency(grandTotal)}`
                )}
              </Button>

              {submit.isError && (
                <p className="mt-3 text-center text-sm text-destructive">
                  {(submit.error as Error).message}
                </p>
              )}
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
