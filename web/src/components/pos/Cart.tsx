import { useMemo, useState } from "react";
import {
  Minus, Plus, X, ShoppingCart, ChevronDown,
  Percent, ReceiptText, PackageMinus,
  CirclePause, Trash2, BadgeDollarSign,
  History, RotateCcw, ArrowLeftRight,
  type LucideIcon,
} from "lucide-react";
import { useCartStore } from "@/stores/cart";
import { formatCurrency, cn } from "@/lib/utils";

interface Props {
  onCheckout: (paymentMode: string) => void;
  /** Mobile sheet close — omit for desktop sidebar */
  onClose?: () => void;
}

const ACTION_ROWS: Array<Array<{
  label: string;
  bgClass: string;
  Icon: LucideIcon;
  action?: "checkout" | "reset";
}>> = [
  [
    { label: "Discount",    bgClass: "bg-[#0E9384]", Icon: Percent        },
    { label: "Tax",         bgClass: "bg-[#6938EF]", Icon: ReceiptText    },
    { label: "Shipping",    bgClass: "bg-[#DD2590]", Icon: PackageMinus   },
  ],
  [
    { label: "Hold",        bgClass: "bg-[#E04F16]", Icon: CirclePause    },
    { label: "Void",        bgClass: "bg-[#155EEF]", Icon: Trash2         },
    { label: "Payment",     bgClass: "bg-[#06AED4]", Icon: BadgeDollarSign, action: "checkout" },
  ],
  [
    { label: "View Orders", bgClass: "bg-[#092C4C]", Icon: History        },
    { label: "Reset",       bgClass: "bg-[#3538CD]", Icon: RotateCcw,      action: "reset" },
    { label: "Transaction", bgClass: "bg-[#FF0000]", Icon: ArrowLeftRight  },
  ],
];

const PAYMENT_METHODS = [
  { label: "Cash",    img: "/assets/surge/images/payment/cash.png",    mode: "Cash"    },
  { label: "Card",    img: "/assets/surge/images/payment/card.png",    mode: "Card"    },
  { label: "Points",  img: "/assets/surge/images/payment/points.png",  mode: "Points"  },
  { label: "Deposit", img: "/assets/surge/images/payment/deposit.png", mode: "Deposit" },
  { label: "Cheque",  img: "/assets/surge/images/payment/cheque.png",  mode: "Cheque"  },
];

export function Cart({ onCheckout, onClose }: Props) {
  const items      = useCartStore((s) => s.items);
  const removeItem = useCartStore((s) => s.removeItem);
  const updateQty  = useCartStore((s) => s.updateQty);
  const clear      = useCartStore((s) => s.clear);
  const grandTotal = useCartStore((s) => s.grandTotalPaise());
  const itemCount  = useCartStore((s) => s.itemCount());

  const [selectedMode, setSelectedMode] = useState("Cash");

  const orderNumber = useMemo(
    () => `#${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
    [],
  );

  return (
    <div className="flex h-full flex-col border-l border-[#E6EAED] bg-white">

      <div className="shrink-0 space-y-2 px-5 py-5 shadow-[0px_4px_60px_rgba(190,190,190,0.27)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-[#212B36]">New Order</span>
            <span className="flex h-5 items-center rounded-[5px] bg-[#6938EF] px-2 text-[10px] font-medium leading-none text-white">
              {orderNumber}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-sm border border-[#FE9F43] px-2.5 py-1 text-xs font-semibold text-[#646B72] transition-colors hover:bg-[#FFF6EE]"
            >
              Add Customer
            </button>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close cart"
                className="text-[#646B72] hover:text-[#212B36]"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex h-9.5 items-center gap-2 rounded-[5px] border border-[#E6EAED] bg-white px-3">
          <span className="flex-1 text-sm text-[#212B36]">Walk-in Customer</span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[#212B36]" />
        </div>
      </div>

      <div className="flex h-11.5 shrink-0 items-center justify-between px-5">
        <span className="text-base font-bold text-black">Order Details</span>
        <div className="flex h-7.5 items-center rounded-sm border border-[#E6EAED] bg-[#F9FAFB] px-2.5 text-xs font-semibold text-[#212B36]">
          Items: {itemCount}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-1 px-4 text-center">
            <ShoppingCart className="mb-2 h-20 w-20 text-[#E6EAED]" strokeWidth={1} />
            <p className="text-sm font-bold text-[#646B72]">No Products Selected</p>
          </div>
        ) : (
          <ul className="divide-y divide-[#E6EAED] px-5">
            {items.map((item) => (
              <li key={item.item_code} className="flex items-center gap-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-bold text-[#212B36]">{item.item_name}</p>
                  <p className="text-xs text-[#646B72]">
                    {formatCurrency(item.rate_paise - item.discount_paise)}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    title="Decrease quantity"
                    onClick={() => updateQty(item.item_code, item.qty - 1)}
                    className="flex h-6 w-6 items-center justify-center rounded-full border border-[#E6EAED] text-[#646B72] transition-colors hover:border-[#6938EF] hover:text-[#6938EF]"
                  >
                    <Minus className="h-3 w-3" />
                  </button>
                  <span className="w-6 text-center text-xs font-bold tabular-nums text-[#212B36]">
                    {item.qty}
                  </span>
                  <button
                    type="button"
                    title="Increase quantity"
                    onClick={() => updateQty(item.item_code, item.qty + 1)}
                    className="flex h-6 w-6 items-center justify-center rounded-full border border-[#E6EAED] text-[#646B72] transition-colors hover:border-[#6938EF] hover:text-[#6938EF]"
                  >
                    <Plus className="h-3 w-3" />
                  </button>
                </div>
                <p className="w-16 text-right text-xs font-bold tabular-nums text-[#212B36]">
                  {formatCurrency((item.rate_paise - item.discount_paise) * item.qty)}
                </p>
                <button
                  type="button"
                  title="Remove item"
                  onClick={() => removeItem(item.item_code)}
                  className="text-[#A6AAAF] transition-colors hover:text-[#DD2590]"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="shrink-0 space-y-5 bg-[#F9FAFB] px-6 py-6">

        <div>
          <div className="flex items-center justify-between rounded-t-md bg-white px-2 py-2">
            <span className="text-sm font-medium leading-5 text-[#646B72]">Sub Total</span>
            <span className="text-sm font-medium tabular-nums text-[#646B72]">
              {formatCurrency(grandTotal)}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-b-[5px] bg-[#E6EAED] px-2 py-2">
            <span className="text-base font-bold text-[#092C4C]">Total</span>
            <span className="text-base font-bold tabular-nums text-[#092C4C]">
              {formatCurrency(grandTotal)}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          {ACTION_ROWS.map((row, ri) => (
            <div key={ri} className="flex gap-2">
              {row.map((btn) => (
                <button
                  key={btn.label}
                  type="button"
                  disabled={btn.action === "checkout" && items.length === 0}
                  onClick={() => {
                    if (btn.action === "checkout") onCheckout(selectedMode);
                    if (btn.action === "reset") clear();
                  }}
                  className={cn(
                    "flex h-7.75 flex-1 items-center justify-center gap-1.5 rounded-[5px] border border-[#E6EAED]",
                    "text-sm font-semibold text-white shadow-[0px_4px_60px_rgba(231,231,231,0.47)]",
                    "transition-opacity disabled:opacity-40",
                    btn.bgClass,
                  )}
                >
                  <btn.Icon className="h-3.5 w-3.5 shrink-0" />
                  {btn.label}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="shrink-0 space-y-4 border-t border-[#E6EAED] px-5 py-5">
        <p className="text-base font-bold text-[#212B36]">Select Payment</p>

        <div className="flex gap-2">
          {PAYMENT_METHODS.map(({ label, img, mode }) => {
            const active = selectedMode === mode;
            return (
              <button
                key={label}
                type="button"
                onClick={() => setSelectedMode(mode)}
                className={cn(
                  "flex h-20.25 flex-1 flex-col items-center justify-center gap-1 rounded-[10px] transition-all",
                  active
                    ? "border border-[#FE9F43] bg-[#FFF6EE]"
                    : "border border-[#E6EAED] bg-white hover:border-[#FE9F43]/50",
                )}
              >
                <img src={img} alt={label} className="h-7 w-7 object-contain" />
                <span className="text-sm font-medium text-[#212B36]">{label}</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          disabled={items.length === 0}
          onClick={() => onCheckout(selectedMode)}
          className="h-12 w-full rounded-lg bg-[#0E9384] text-sm font-bold text-white transition-opacity disabled:opacity-40 hover:bg-[#0c8175]"
        >
          Grand Total: {formatCurrency(grandTotal)}
        </button>
      </div>
    </div>
  );
}
