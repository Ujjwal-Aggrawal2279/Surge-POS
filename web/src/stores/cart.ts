import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { persist, createJSONStorage } from "zustand/middleware";
import type { CartItem, PaymentEntry } from "@/types/pos";
import { paise } from "@/lib/utils";

interface CartState {
  items: CartItem[];
  customer: string;
  payments: PaymentEntry[];
  recoveredFromCrash: boolean;

  addItem: (item: Omit<CartItem, "qty"> & { qty?: number }) => void;
  removeItem: (item_code: string) => void;
  updateQty: (item_code: string, qty: number) => void;
  updateDiscount: (item_code: string, discount_paise: number) => void;
  setCustomer: (customer: string) => void;
  setPayments: (payments: PaymentEntry[]) => void;
  clear: () => void;
  acknowledgeRecovery: () => void;

  grandTotalPaise: () => number;
  itemCount: () => number;
}

export const useCartStore = create<CartState>()(
  persist(
    immer((set, get) => ({
      items: [],
      customer: "Walk-in Customer",
      payments: [],
      recoveredFromCrash: false,

      addItem(item) {
        set((s) => {
          const existing = s.items.find((i) => i.item_code === item.item_code);
          if (existing) {
            existing.qty += item.qty ?? 1;
          } else {
            s.items.push({ ...item, qty: item.qty ?? 1 });
          }
        });
      },

      removeItem(item_code) {
        set((s) => {
          s.items = s.items.filter((i) => i.item_code !== item_code);
        });
      },

      updateQty(item_code, qty) {
        set((s) => {
          const item = s.items.find((i) => i.item_code === item_code);
          if (!item) return;
          if (qty <= 0) {
            s.items = s.items.filter((i) => i.item_code !== item_code);
          } else {
            item.qty = qty;
          }
        });
      },

      updateDiscount(item_code, discount_paise) {
        set((s) => {
          const item = s.items.find((i) => i.item_code === item_code);
          if (item) item.discount_paise = discount_paise;
        });
      },

      setCustomer(customer) {
        set((s) => { s.customer = customer; });
      },

      setPayments(payments) {
        set((s) => { s.payments = payments; });
      },

      clear() {
        set((s) => {
          s.items = [];
          s.payments = [];
          s.customer = "Walk-in Customer";
          s.recoveredFromCrash = false;
        });
      },

      acknowledgeRecovery() {
        set((s) => { s.recoveredFromCrash = false; });
      },

      grandTotalPaise() {
        return get().items.reduce(
          (sum, item) => sum + (item.rate_paise - item.discount_paise) * item.qty,
          0,
        );
      },

      itemCount() {
        return get().items.reduce((n, i) => n + i.qty, 0);
      },
    })),
    {
      name: "surge-cart-v1",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        items: s.items,
        customer: s.customer,
        payments: s.payments,
        recoveredFromCrash: s.items.length > 0,
      }),
      version: 1,
      migrate: (persisted, _version) => persisted as CartState,
    },
  ),
);

export { paise };
