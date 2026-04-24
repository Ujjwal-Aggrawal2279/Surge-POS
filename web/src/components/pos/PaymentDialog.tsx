import { useState, useEffect, useRef } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Loader2, CheckCircle2, WifiOff, Banknote, CreditCard, Smartphone, Wallet } from "lucide-react";
import { useCartStore } from "@/stores/cart";
import { useSubmitInvoice } from "@/hooks/useInvoice";
import { formatCurrency, cn } from "@/lib/utils";

const FALLBACK_PAYMENT_MODES = ["Cash", "Card", "UPI"];

const MODE_ICONS: Record<string, React.ReactNode> = {
  Cash:   <Banknote className="h-5 w-5" />,
  Card:   <CreditCard className="h-5 w-5" />,
  UPI:    <Smartphone className="h-5 w-5" />,
};
function modeIcon(m: string) {
  return MODE_ICONS[m] ?? <Wallet className="h-5 w-5" />;
}

interface Props {
  open: boolean;
  onClose: () => void;
  posProfile: string;
  paymentModes?: string[];
  defaultMode?: string;
  approvalToken?: string;
}

export function PaymentDialog({ open, onClose, posProfile, paymentModes, defaultMode, approvalToken }: Props) {
  const modes = paymentModes?.length ? paymentModes : FALLBACK_PAYMENT_MODES;
  const items      = useCartStore((s) => s.items);
  const customer   = useCartStore((s) => s.customer);
  const grandTotal = useCartStore((s) => s.grandTotalPaise());
  const clear      = useCartStore((s) => s.clear);

  const [mode, setMode] = useState(defaultMode ?? "Cash");
  const [tendered, setTendered] = useState("");
  const [result, setResult] = useState<{ invoiceName: string | null; status: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setMode(defaultMode ?? "Cash");
      setTendered("");
      setResult(null);
    }
  }, [open, defaultMode]);

  useEffect(() => {
    if (open && mode === "Cash") setTimeout(() => inputRef.current?.focus(), 80);
  }, [open, mode]);

  const submit = useSubmitInvoice();

  const tenderedPaise = Math.round(parseFloat(tendered || "0") * 100);
  const changePaise   = tenderedPaise - grandTotal;
  const isCash        = mode === "Cash";
  const canCharge     = !isCash || tenderedPaise >= grandTotal || tendered === "";

  async function handleCharge() {
    const res = await submit.mutateAsync({
      items,
      customer,
      pos_profile: posProfile,
      payments: [{ mode_of_payment: mode, amount_paise: grandTotal }],
      approval_token: approvalToken,
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
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white shadow-2xl outline-none">

          {result ? (
            <SuccessState result={result} grandTotal={grandTotal} onDone={handleDone} />
          ) : (
            <>
              {/* Header */}
              <div className="flex items-center justify-between border-b border-[#E6EAED] px-5 py-4">
                <Dialog.Title className="text-sm font-bold text-[#212B36]">Payment</Dialog.Title>
                <Dialog.Close asChild>
                  <button
                    type="button"
                    disabled={submit.isPending}
                    title="Close"
                    className="rounded-lg p-1 text-[#646B72] hover:bg-[#F4F6F8] hover:text-[#212B36]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </Dialog.Close>
              </div>

              {/* Amount */}
              <div className="px-5 py-5 text-center">
                <p className="text-xs font-medium text-[#919EAB] uppercase tracking-wide mb-1">Total Due</p>
                <p className="text-4xl font-bold text-[#212B36] tabular-nums">{formatCurrency(grandTotal)}</p>
                {customer && (
                  <p className="mt-1.5 text-xs text-[#646B72]">
                    Customer: <span className="font-semibold">{customer}</span>
                  </p>
                )}
              </div>

              {/* Payment mode chips */}
              <div className="grid grid-cols-3 gap-2 px-5 pb-4">
                {modes.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => { setMode(m); setTendered(""); }}
                    className={cn(
                      "flex flex-col items-center gap-1.5 rounded-xl border py-3 text-xs font-semibold transition-all",
                      mode === m
                        ? "border-[#0E9384] bg-[#F0FAFA] text-[#0E9384] shadow-sm"
                        : "border-[#E6EAED] text-[#646B72] hover:border-[#0E9384]/40 hover:text-[#0E9384]",
                    )}
                  >
                    {modeIcon(m)}
                    {m}
                  </button>
                ))}
              </div>

              {/* Cash tendered */}
              {isCash && (
                <div className="mx-5 mb-4 rounded-xl border border-[#E6EAED] bg-[#F8FAFB] p-4">
                  <label className="mb-1.5 block text-xs font-semibold text-[#212B36]">
                    Cash Tendered
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[#646B72]">₹</span>
                    <input
                      ref={inputRef}
                      type="number"
                      inputMode="decimal"
                      min={0}
                      step={0.5}
                      value={tendered}
                      onChange={(e) => setTendered(e.target.value)}
                      placeholder={`${(grandTotal / 100).toFixed(2)}`}
                      className="flex-1 bg-transparent text-xl font-bold text-[#212B36] outline-none placeholder:text-[#C4CDD5]"
                    />
                  </div>
                  {tendered !== "" && tenderedPaise >= grandTotal && (
                    <div className="mt-3 flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2">
                      <span className="text-xs font-semibold text-emerald-700">Change</span>
                      <span className="text-sm font-bold text-emerald-700 tabular-nums">
                        {formatCurrency(changePaise)}
                      </span>
                    </div>
                  )}
                  {tendered !== "" && tenderedPaise < grandTotal && (
                    <div className="mt-3 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2">
                      <span className="text-xs font-semibold text-red-600">Short by</span>
                      <span className="text-sm font-bold text-red-600 tabular-nums">
                        {formatCurrency(grandTotal - tenderedPaise)}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Error */}
              {submit.isError && (
                <p className="mx-5 mb-3 rounded-lg bg-red-50 px-3 py-2 text-center text-sm text-red-600">
                  {(submit.error as Error).message}
                </p>
              )}

              {/* Charge button */}
              <div className="px-5 pb-5">
                <button
                  type="button"
                  disabled={submit.isPending || !canCharge}
                  onClick={handleCharge}
                  className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#0E9384] text-sm font-bold text-white transition-colors hover:bg-[#0c8175] disabled:opacity-40"
                >
                  {submit.isPending ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Processing…</>
                  ) : (
                    `Charge ${formatCurrency(grandTotal)}`
                  )}
                </button>
              </div>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function SuccessState({
  result,
  grandTotal,
  onDone,
}: {
  result: { invoiceName: string | null; status: string };
  grandTotal: number;
  onDone: () => void;
}) {
  const ok = result.status === "submitted";
  return (
    <div className="flex flex-col items-center gap-3 px-8 py-10 text-center">
      {ok ? (
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50">
          <CheckCircle2 className="h-9 w-9 text-emerald-500" />
        </div>
      ) : (
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
          <WifiOff className="h-9 w-9 text-amber-500" />
        </div>
      )}

      <div>
        <p className="text-base font-bold text-[#212B36]">
          {ok ? "Payment Collected" : "Saved Offline"}
        </p>
        <p className="mt-0.5 text-xs text-[#919EAB]">
          {ok
            ? result.invoiceName ?? ""
            : "Will sync automatically when online"}
        </p>
      </div>

      <p className="text-3xl font-bold text-[#212B36] tabular-nums">{formatCurrency(grandTotal)}</p>

      <button
        type="button"
        onClick={onDone}
        className="mt-2 flex h-11 w-full items-center justify-center rounded-xl bg-[#0E9384] text-sm font-bold text-white hover:bg-[#0c8175]"
      >
        New Sale
      </button>
    </div>
  );
}
