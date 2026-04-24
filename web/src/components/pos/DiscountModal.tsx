import { useState, useMemo } from "react";
import { X, AlertTriangle, ShieldCheck, Check } from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";
import { ManagerApprovalModal } from "./ManagerApprovalModal";
import type { CartItem, Cashier } from "@/types/pos";

interface Props {
  items: CartItem[];
  cashier: Cashier;
  discountLimitPct: number;
  posProfile: string;
  onApply: (discounts: Record<string, number>, approvalToken?: string) => void;
  onClose: () => void;
}

export function DiscountModal({ items, cashier, discountLimitPct, posProfile, onApply, onClose }: Props) {
  const [inputs, setInputs] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      items.map((i) => [
        i.item_code,
        i.rate_paise > 0 ? ((i.discount_paise / i.rate_paise) * 100).toFixed(1) : "0",
      ]),
    ),
  );
  const [approvalModal, setApprovalModal] = useState(false);
  const [approvalToken, setApprovalToken] = useState<string | undefined>();
  const [approvedBy, setApprovedBy] = useState<string | undefined>();

  const maxPct = useMemo(() => {
    return Math.max(
      ...items.map((i) => {
        const v = parseFloat(inputs[i.item_code] || "0");
        return isNaN(v) ? 0 : v;
      }),
    );
  }, [inputs, items]);

  const needsApproval = maxPct > discountLimitPct;
  const approved = needsApproval && !!approvalToken;

  function handleApply() {
    if (needsApproval && !approvalToken) {
      setApprovalModal(true);
      return;
    }
    const discounts: Record<string, number> = {};
    for (const item of items) {
      const pct = parseFloat(inputs[item.item_code] || "0");
      discounts[item.item_code] = isNaN(pct) ? 0 : Math.round((pct / 100) * item.rate_paise);
    }
    onApply(discounts, approvalToken);
    onClose();
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-bold text-[#212B36]">Apply Discount</h2>
            <button type="button" onClick={onClose} className="text-[#646B72] hover:text-[#212B36]">
              <X className="h-4 w-4" />
            </button>
          </div>

          <p className="mb-1 text-xs text-[#646B72]">
            Your limit as <strong>{cashier.access_level}</strong>:{" "}
            <strong>{discountLimitPct}%</strong>
          </p>

          <div className="mb-4 max-h-64 overflow-y-auto divide-y divide-[#E6EAED]">
            {items.map((item) => {
              const pct = parseFloat(inputs[item.item_code] || "0");
              const exceeds = !isNaN(pct) && pct > discountLimitPct;
              return (
                <div key={item.item_code} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-[#212B36]">{item.item_name}</p>
                    <p className="text-xs text-[#646B72]">{formatCurrency(item.rate_paise)}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={inputs[item.item_code]}
                      onChange={(e) => {
                        setApprovalToken(undefined);
                        setApprovedBy(undefined);
                        setInputs((prev) => ({ ...prev, [item.item_code]: e.target.value }));
                      }}
                      className={cn(
                        "w-16 rounded-lg border px-2 py-1 text-right text-sm outline-none",
                        exceeds
                          ? "border-amber-400 bg-amber-50 text-amber-700"
                          : "border-[#E6EAED] text-[#212B36] focus:border-[#0E9384]",
                      )}
                    />
                    <span className="text-xs text-[#646B72]">%</span>
                  </div>
                </div>
              );
            })}
          </div>

          {needsApproval && !approved && (
            <div className="mb-4 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Discount exceeds your {discountLimitPct}% limit. Manager approval required.
              </span>
            </div>
          )}

          {approved && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700">
              <Check className="h-4 w-4 shrink-0" />
              <span>Approved by <strong>{approvedBy}</strong></span>
            </div>
          )}

          <button
            type="button"
            onClick={handleApply}
            className={cn(
              "flex h-10 w-full items-center justify-center gap-2 rounded-lg text-sm font-bold text-white transition-colors",
              needsApproval && !approved
                ? "bg-amber-500 hover:bg-amber-600"
                : "bg-[#0E9384] hover:bg-[#0c8175]",
            )}
          >
            {needsApproval && !approved ? (
              <><ShieldCheck className="h-4 w-4" /> Request Approval</>
            ) : (
              "Apply Discount"
            )}
          </button>
        </div>
      </div>

      {approvalModal && (
        <ManagerApprovalModal
          posProfile={posProfile}
          action="discount_override"
          onApproved={(token, approver) => {
            setApprovalToken(token);
            setApprovedBy(approver.full_name);
            setApprovalModal(false);
          }}
          onClose={() => setApprovalModal(false)}
        />
      )}
    </>
  );
}
