import { useState, useEffect } from "react";
import { AlertTriangle, Loader2, Store } from "lucide-react";
import { useSession } from "@/hooks/useSession";
import { formatCurrency } from "@/lib/utils";
import type { POSProfile, Session } from "@/types/pos";

interface Props {
  profile: POSProfile;
  onSessionOpen: (session: Session) => void;
}

export function ShiftOpen({ profile, onSessionOpen }: Props) {
  const { session, stale, loading, error, openSession } = useSession(profile.name);
  const [amounts, setAmounts] = useState<Record<string, string>>(() =>
    Object.fromEntries(profile.payment_modes.map((m) => [m, ""])),
  );
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Auto-advance if an active session already exists (cashier handover / reconnect)
  useEffect(() => {
    if (session) onSessionOpen(session);
  }, [session, onSessionOpen]);

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!profile.payment_modes.length) {
    return (
      <div className="flex h-dvh items-center justify-center p-4">
        <p className="text-sm text-destructive">
          No payment modes configured on this POS Profile. Contact your manager.
        </p>
      </div>
    );
  }

  async function handleOpen() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const balances = profile.payment_modes.map((m) => ({
        mode_of_payment: m,
        amount: parseFloat(amounts[m] ?? "0") || 0,
      }));
      const result = await openSession(balances);
      onSessionOpen({
        name: result.session_name,
        period_start_date: result.period_start_date,
        user: window.SURGE_CONFIG.user,
      });
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const totalPaise = profile.payment_modes.reduce((sum, m) => {
    return sum + Math.round((parseFloat(amounts[m] ?? "0") || 0) * 100);
  }, 0);

  return (
    <div className="flex h-dvh flex-col items-center justify-center bg-[#F7F7F7] p-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-background shadow-xl">
        <div className="border-b border-border px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
              <Store className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">Open Shift</h1>
              <p className="text-xs text-muted-foreground">{profile.name}</p>
            </div>
          </div>
        </div>

        <div className="px-6 py-5 space-y-4">
          {stale ? (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-4 text-sm">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
              <div>
                <p className="font-semibold text-red-800">Previous shift was not closed</p>
                <p className="mt-1 text-red-700">
                  Yesterday's shift is still open. A <strong>Manager</strong> must close it
                  from the Manager Dashboard before you can start today's session.
                </p>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Enter the opening float for each payment mode.
              </p>

              {profile.payment_modes.map((mode) => (
                <div key={mode} className="flex items-center gap-3">
                  <label className="w-32 shrink-0 text-sm font-medium text-foreground">{mode}</label>
                  <div className="relative flex-1">
                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">₹</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={amounts[mode] ?? ""}
                      onChange={(e) => setAmounts((prev) => ({ ...prev, [mode]: e.target.value }))}
                      className="w-full rounded-lg border border-input bg-background pl-7 pr-3 py-2 text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>
              ))}

              {totalPaise > 0 && (
                <div className="flex items-center justify-between rounded-lg bg-muted px-4 py-2 text-sm">
                  <span className="text-muted-foreground">Total opening float</span>
                  <span className="font-semibold tabular-nums">{formatCurrency(totalPaise)}</span>
                </div>
              )}

              {(submitError ?? error) && (
                <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
                  {submitError ?? error}
                </p>
              )}
            </>
          )}
        </div>

        <div className="border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={handleOpen}
            disabled={stale || submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60 active:scale-[0.99]"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Opening shift…
              </>
            ) : (
              "Open Shift"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
