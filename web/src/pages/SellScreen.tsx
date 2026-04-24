import React, { useState, useMemo } from "react";
import { useItems, useItemPrices, useStock } from "@/hooks/useItems";
import { ItemGrid, buildPriceMap, buildStockMap } from "@/components/pos/ItemGrid";
import { Cart } from "@/components/pos/Cart";
import { PaymentDialog } from "@/components/pos/PaymentDialog";
import { useCartStore } from "@/stores/cart";
import { useIdleLock } from "@/hooks/useIdleLock";
import { config, post } from "@/lib/api";
import { clearSession } from "@/lib/session";
import { formatCurrency, cn } from "@/lib/utils";
import { Loader2, Lock, Monitor, ShoppingCart, LogOut, Clock } from "lucide-react";
import { ApprovalQueue } from "@/components/pos/ApprovalQueue";
import type { Cashier, POSProfile } from "@/types/pos";

const IDLE_TIMEOUT_MS = 15 * 60 * 1000;
const IDLE_WARN_MS    = 15 * 1000;      // warn 15s before

interface Props {
  profile: POSProfile;
  cashier: Cashier;
  onLock: () => void;
  onChangeProfile: () => void;
}

export function SellScreen({ profile, cashier, onLock, onChangeProfile }: Props) {
  const cfg = config();
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [paymentMode, setPaymentMode] = useState(() => profile.payment_modes?.[0] ?? "Cash");
  const [approvalToken, setApprovalToken] = useState<string | undefined>();
  const [mobileCartOpen, setMobileCartOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false);

  const { isWarning: idleWarning, secondsLeft, dismissWarning } = useIdleLock(
    IDLE_TIMEOUT_MS,
    onLock,
    { warnBeforeMs: IDLE_WARN_MS, disabled: paymentOpen || logoutConfirmOpen },
  );

  function handleCheckout(mode: string, token?: string) {
    setPaymentMode(mode);
    setApprovalToken(token);
    setPaymentOpen(true);
  }

  async function confirmLogout() {
    setLoggingOut(true);
    try {
      clearSession();
      onChangeProfile();
      await post("logout");
    } catch {
      // logout endpoint may not return clean JSON — redirect anyway
    }
    window.location.href = "/surge";
  }

  // Mobile cart summary — read store at top level (rules of hooks)
  const cartItemCount = useCartStore((s) => s.itemCount());
  const cartTotal = useCartStore((s) => s.grandTotalPaise());

  React.useEffect(() => {
    const up = () => setIsOnline(true);
    const down = () => setIsOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => { window.removeEventListener("online", up); window.removeEventListener("offline", down); };
  }, []);

  const items = useItems(profile.name);
  const prices = useItemPrices(profile.name);
  const stock = useStock(profile.warehouse);

  const priceMap = useMemo(
    () => buildPriceMap(prices.data?.prices ?? []),
    [prices.data],
  );
  const stockMap = useMemo(
    () => buildStockMap(stock.data?.stock ?? []),
    [stock.data],
  );

  const loading = items.isLoading || prices.isLoading;
  const error = items.error || prices.error;

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-dvh items-center justify-center text-destructive">
        <p>Failed to load: {(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-[#F7F7F7]">
      {/* ── Navbar (keep as-is, per design brief) ─────────────────── */}
      <header className="flex shrink-0 items-center justify-between border-b bg-background px-4 py-2">
        <span className="font-bold tracking-tight text-primary">Surge POS</span>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">

          {/* Online / Offline pill */}
          <span className={cn(
            "flex items-center gap-1.5 rounded-full px-2 py-0.5 font-medium",
            isOnline ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600",
          )}>
            <span className={cn(
              "h-1.5 w-1.5 rounded-full",
              isOnline ? "bg-emerald-500" : "bg-amber-500 animate-pulse",
            )} />
            {isOnline ? "Online" : "Offline"}
          </span>

          <span className="hidden sm:inline">{profile.name}</span>
          <span className="hidden sm:inline text-muted-foreground/40">·</span>
          <span>{cashier.full_name}</span>

          {/* Approval queue — Supervisors and Managers only */}
          {(cashier.access_level === "Supervisor" || cashier.access_level === "Manager") && (
            <ApprovalQueue accessLevel={cashier.access_level} />
          )}

          {/* Switch to Desk — only for desk users */}
          {cfg.has_desk_access === 1 && (
            <a
              href="/app"
              className="flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-muted-foreground hover:border-primary/50 hover:text-foreground"
              title="Switch to Frappe Desk"
            >
              <Monitor className="h-3 w-3" />
              <span className="hidden sm:inline">Desk</span>
            </a>
          )}

          {/* Lock */}
          <button
            type="button"
            onClick={onLock}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-muted-foreground hover:border-primary/50 hover:text-foreground"
            title="Lock terminal — requires PIN to resume"
          >
            <Lock className="h-3 w-3" />
            <span className="hidden sm:inline">Lock</span>
          </button>

          {/* Logout */}
          <button
            type="button"
            onClick={() => setLogoutConfirmOpen(true)}
            disabled={loggingOut}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-muted-foreground hover:border-red-300 hover:text-red-600 disabled:opacity-50"
            title="Log out completely"
          >
            <LogOut className="h-3 w-3" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      {/* Idle lock warning banner */}
      {idleWarning && (
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          <span className="flex items-center gap-2">
            <Clock className="h-4 w-4 shrink-0" />
            Terminal will lock in <strong>{secondsLeft}s</strong> due to inactivity.
          </span>
          <button
            type="button"
            onClick={dismissWarning}
            className="rounded-md border border-amber-300 bg-amber-100 px-3 py-0.5 text-xs font-semibold text-amber-800 hover:bg-amber-200"
          >
            I'm here
          </button>
        </div>
      )}

      {/* ── Main layout: items (left) + cart (right) ──────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left — item grid */}
        <main className="flex-1 overflow-hidden p-4">
          <ItemGrid
            items={items.data?.items ?? []}
            prices={priceMap}
            stock={stockMap}
            warehouse={profile.warehouse}
            cashier={cashier}
          />
        </main>

        {/* Right — cart sidebar (desktop) */}
        <aside className="hidden w-117.5 shrink-0 md:flex md:flex-col">
          <Cart
            onCheckout={handleCheckout}
            cashier={cashier}
            posProfile={profile}
          />
        </aside>
      </div>

      {/* ── Mobile: sticky cart bar ────────────────────────────────── */}
      <div className="flex shrink-0 items-center justify-between border-t bg-background px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">
            {cartItemCount === 0 ? "Empty" : `${cartItemCount} item${cartItemCount > 1 ? "s" : ""}`}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {cartItemCount > 0 && (
            <span className="text-sm font-semibold tabular-nums">{formatCurrency(cartTotal)}</span>
          )}
          <button
            type="button"
            onClick={() => setMobileCartOpen(true)}
            disabled={cartItemCount === 0}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-40 active:bg-primary/90"
          >
            View Cart
          </button>
        </div>
      </div>

      {/* ── Mobile: cart bottom sheet ─────────────────────────────── */}
      {mobileCartOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileCartOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 flex max-h-[85dvh] flex-col overflow-hidden rounded-t-2xl bg-background shadow-2xl">
            <Cart
              onCheckout={(mode, token) => { setMobileCartOpen(false); handleCheckout(mode, token); }}
              cashier={cashier}
              posProfile={profile}
              onClose={() => setMobileCartOpen(false)}
            />
          </div>
        </div>
      )}

      <PaymentDialog
        open={paymentOpen}
        onClose={() => setPaymentOpen(false)}
        posProfile={profile.name}
        paymentModes={profile.payment_modes}
        defaultMode={paymentMode}
        approvalToken={approvalToken}
      />

      {/* ── Logout confirmation modal ──────────────────────────────── */}
      {logoutConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-2xl border border-border bg-background p-6 shadow-2xl">
            <div className="mb-1 flex items-center gap-2">
              <LogOut className="h-4 w-4 text-red-500" />
              <h2 className="text-base font-semibold">Log out?</h2>
            </div>
            <p className="mb-5 text-sm text-muted-foreground">
              This will end your session on this terminal. You'll need to sign in again to continue.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setLogoutConfirmOpen(false)}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmLogout}
                disabled={loggingOut}
                className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-60"
              >
                {loggingOut ? <Loader2 className="h-3 w-3 animate-spin" /> : <LogOut className="h-3 w-3" />}
                {loggingOut ? "Logging out…" : "Log out"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
