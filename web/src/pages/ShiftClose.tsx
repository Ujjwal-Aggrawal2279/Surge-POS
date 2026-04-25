import { useState } from "react";
import { Loader2, Printer, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import type { POSProfile, ZReport, ZReportMode } from "@/types/pos";

interface Props {
  profile: POSProfile;
  openingEntry: string;
  onClose: (zReport: ZReport) => void;
  onCancel: () => void;
  closeSession: (
    openingEntry: string,
    closingBalances: { mode_of_payment: string; amount: number }[],
    discrepancyReason?: string,
  ) => Promise<ZReport>;
}

// ── Z-Report display ─────────────────────────────────────────────────────────

function ZReportView({ report, onDone }: { report: ZReport; onDone: () => void }) {
  function handlePrint() { window.print(); }

  const hasDiscrepancy = report.payment_modes.some((m) => m.discrepancy_paise !== 0);

  return (
    <div className="flex h-dvh flex-col bg-[#F7F7F7] print:bg-white">
      <header className="flex shrink-0 items-center justify-between border-b bg-background px-6 py-3 print:border-none">
        <div>
          <h1 className="text-base font-semibold">Z-Report</h1>
          <p className="text-xs text-muted-foreground">{report.pos_profile}</p>
        </div>
        <div className="flex gap-2 print:hidden">
          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted"
          >
            <Printer className="h-3.5 w-3.5" />
            Print
          </button>
          <button
            type="button"
            onClick={onDone}
            className="rounded-lg bg-primary px-4 py-1.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          >
            New Shift
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4 max-w-xl mx-auto w-full">
        {/* Period */}
        <div className="rounded-xl border border-border bg-background p-4 space-y-1">
          <Row label="Cashier" value={report.cashier} />
          <Row label="Shift start" value={new Date(report.period_start).toLocaleString()} />
          <Row label="Shift end" value={new Date(report.period_end).toLocaleString()} />
        </div>

        {/* Sales summary */}
        <div className="rounded-xl border border-border bg-background p-4 space-y-1">
          <Row label="Total sales" value={String(report.total_invoices)} />
          <Row label="Total returns" value={String(report.total_returns)} />
          <Row label="Net sales" value={formatCurrency(report.net_sales_paise)} bold />
          <Row label="Net returns" value={formatCurrency(report.net_returns_paise)} />
          <Row label="Tax collected" value={formatCurrency(report.total_tax_paise)} />
        </div>

        {/* Payment modes */}
        <div className="rounded-xl border border-border bg-background p-4">
          <h2 className="mb-3 text-sm font-semibold">Cash Reconciliation</h2>
          <div className="space-y-3">
            {report.payment_modes.map((mode) => (
              <ModeRow key={mode.mode_of_payment} mode={mode} />
            ))}
          </div>
        </div>

        {/* Discrepancy warning */}
        {hasDiscrepancy && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <strong>Discrepancies found.</strong> Review with manager before closing.
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm tabular-nums ${bold ? "font-semibold" : ""}`}>{value}</span>
    </div>
  );
}

function ModeRow({ mode }: { mode: ZReportMode }) {
  const disc = mode.discrepancy_paise;
  const Icon = disc > 0 ? TrendingUp : disc < 0 ? TrendingDown : Minus;
  const discColor = disc > 0 ? "text-green-600" : disc < 0 ? "text-red-600" : "text-muted-foreground";

  return (
    <div className="rounded-lg border border-border p-3 space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{mode.mode_of_payment}</span>
        <span className={`flex items-center gap-1 text-xs font-medium ${discColor}`}>
          <Icon className="h-3 w-3" />
          {disc === 0 ? "Balanced" : formatCurrency(Math.abs(disc))}
          {disc !== 0 && (disc > 0 ? " over" : " short")}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        <div>
          <div className="font-medium text-foreground/70">Opening</div>
          <div className="tabular-nums">{formatCurrency(mode.opening_amount_paise)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground/70">Sales</div>
          <div className="tabular-nums">{formatCurrency(mode.sales_amount_paise)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground/70">Expected</div>
          <div className="tabular-nums">{formatCurrency(mode.expected_amount_paise)}</div>
        </div>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Counted</span>
        <span className={`tabular-nums font-semibold ${discColor}`}>
          {formatCurrency(mode.actual_amount_paise)}
        </span>
      </div>
    </div>
  );
}

// ── Blind close form ─────────────────────────────────────────────────────────

export function ShiftClose({ profile, openingEntry, onClose, onCancel, closeSession }: Props) {
  const [amounts, setAmounts] = useState<Record<string, string>>(() =>
    Object.fromEntries(profile.payment_modes.map((m) => [m, ""])),
  );
  const [discrepancyReason, setDiscrepancyReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zReport, setZReport] = useState<ZReport | null>(null);

  if (!profile.payment_modes.length) {
    return (
      <div className="flex h-dvh items-center justify-center p-4">
        <p className="text-sm text-destructive">
          No payment modes configured on this POS Profile. Contact your manager.
        </p>
      </div>
    );
  }

  if (zReport) {
    return <ZReportView report={zReport} onDone={() => onClose(zReport)} />;
  }

  async function handleClose() {
    setSubmitting(true);
    setError(null);
    try {
      const balances = profile.payment_modes.map((m) => ({
        mode_of_payment: m,
        amount: parseFloat(amounts[m] ?? "0") || 0,
      }));
      const report = await closeSession(openingEntry, balances, discrepancyReason);
      setZReport(report);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex h-dvh flex-col items-center justify-center bg-[#F7F7F7] p-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-background shadow-xl">
        <div className="border-b border-border px-6 py-5">
          <h1 className="text-lg font-semibold">Close Shift</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Count your cash first. Totals are revealed after submission.
          </p>
        </div>

        <div className="px-6 py-5 space-y-4">
          {profile.payment_modes.map((mode) => (
            <div key={mode} className="flex items-center gap-3">
              <label className="w-32 shrink-0 text-sm font-medium">{mode}</label>
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

          <div>
            <label className="mb-1 block text-sm font-medium">
              Discrepancy reason <span className="text-muted-foreground">(optional)</span>
            </label>
            <textarea
              rows={2}
              placeholder="e.g. Cash counted before last sale was entered"
              value={discrepancyReason}
              onChange={(e) => setDiscrepancyReason(e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <div className="flex gap-2 border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border border-border px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-muted"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleClose}
            disabled={submitting}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-destructive px-4 py-3 text-sm font-semibold text-white hover:bg-destructive/90 disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Closing…
              </>
            ) : (
              "Close Shift"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
