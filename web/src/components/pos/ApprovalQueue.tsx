import { useState, useEffect, useRef } from "react";
import { ShieldCheck, X, Loader2, Bell, Check, XCircle } from "lucide-react";
import { get, post, hashPin } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DiscountItem { item_name: string; pct: number }

interface PendingRequest {
  req_id: string;
  cashier_name: string;
  pos_profile: string;
  action: string;
  created_at: string;
  meta?: string;
}

interface Props {
  accessLevel: "Supervisor" | "Manager";
}

export function ApprovalQueue({ accessLevel }: Props) {
  const [open, setOpen]           = useState(false);
  const [requests, setRequests]   = useState<PendingRequest[]>([]);
  const [active, setActive]       = useState<PendingRequest | null>(null);
  const [pin, setPin]             = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]         = useState("");
  const pinRef = useRef<HTMLInputElement>(null);

  // Fetch queue on mount
  useEffect(() => {
    fetchQueue();
  }, []);

  // Realtime: new request / cancellation
  useEffect(() => {
    const onRequest = (ev: unknown) => {
      const d = ev as PendingRequest & { req_id: string };
      setRequests((prev) => {
        if (prev.some((r) => r.req_id === d.req_id)) return prev;
        return [d, ...prev];
      });
    };
    const onCancelled = (ev: unknown) => {
      const d = ev as { req_id: string };
      setRequests((prev) => prev.filter((r) => r.req_id !== d.req_id));
      setActive((a) => (a?.req_id === d.req_id ? null : a));
    };

    const rt = window.frappe?.realtime;
    rt?.on("surge:approval_request", onRequest);
    rt?.on("surge:approval_cancelled", onCancelled);

    // Fallback poll every 30s — catches missed events if socket drops
    const pollTimer = setInterval(fetchQueue, 30_000);

    return () => {
      clearInterval(pollTimer);
      rt?.off("surge:approval_request", onRequest);
      rt?.off("surge:approval_cancelled", onCancelled);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchQueue() {
    try {
      const res = await get<{ requests: PendingRequest[] }>("surge.api.auth.get_pending_approvals");
      setRequests(res.requests ?? []);
    } catch { /* silently ignore */ }
  }

  function openRequest(req: PendingRequest) {
    setActive(req);
    setPin("");
    setError("");
    setTimeout(() => pinRef.current?.focus(), 80);
  }

  async function respond(decision: "approve" | "deny") {
    if (!active || pin.length < 4) return;
    setSubmitting(true);
    setError("");
    try {
      const pinHash = await hashPin(pin);
      const res = await post<{ status: string; message?: string }>(
        "surge.api.auth.respond_to_approval",
        { req_id: active.req_id, pin: pinHash, decision },
      );
      if (res.status === "ok") {
        setRequests((prev) => prev.filter((r) => r.req_id !== active.req_id));
        setActive(null);
        if (requests.length <= 1) setOpen(false);
      } else if (res.status === "wrong_pin") {
        setError("Incorrect PIN. Try again.");
        setPin("");
        pinRef.current?.focus();
      } else {
        setError(res.message ?? "Something went wrong.");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const count = requests.length;

  return (
    <div className="relative">
      {/* Bell button */}
      <button
        type="button"
        onClick={() => { setOpen((o) => !o); if (!open) fetchQueue(); }}
        className={cn(
          "relative flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors",
          count > 0
            ? "border-[#6938EF]/40 bg-[#F4F3FF] text-[#6938EF] hover:bg-[#ede9fe]"
            : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground",
        )}
        title="Pending approvals"
      >
        <Bell className="h-3 w-3" />
        <span className="hidden sm:inline">Approvals</span>
        {count > 0 && (
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[#6938EF] text-[10px] font-bold text-white">
            {count}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => { setOpen(false); setActive(null); }} />
          <div className="absolute right-0 top-8 z-50 w-80 rounded-xl border border-[#E6EAED] bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#E6EAED] px-4 py-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#6938EF]" />
                <span className="text-sm font-bold text-[#212B36]">Pending Approvals</span>
              </div>
              <button type="button" title="Close" onClick={() => { setOpen(false); setActive(null); }}
                className="text-[#646B72] hover:text-[#212B36]">
                <X className="h-4 w-4" />
              </button>
            </div>

            {requests.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-[#919EAB]">No pending requests</p>
            ) : !active ? (
              <ul className="max-h-64 overflow-y-auto divide-y divide-[#F4F6F8]">
                {requests.map((req) => (
                  <li key={req.req_id}>
                    <button type="button" onClick={() => openRequest(req)}
                      className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-[#F8FAFB] transition-colors">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#F4F3FF]">
                        <ShieldCheck className="h-4 w-4 text-[#6938EF]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold text-[#212B36]">{req.cashier_name}</p>
                        <p className="text-[11px] text-[#919EAB]">requesting {req.action.replace(/_/g, " ")}</p>
                      </div>
                      <span className="shrink-0 text-[10px] font-medium text-[#6938EF]">Review →</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-4">
                <button type="button" onClick={() => setActive(null)}
                  className="mb-3 flex items-center gap-1 text-xs text-[#646B72] hover:text-[#212B36]">
                  ← Back
                </button>
                <p className="mb-1 text-xs font-semibold text-[#212B36]">Request from {active.cashier_name}</p>
                <p className="mb-2 text-xs text-[#919EAB]">
                  Action: <span className="font-medium text-[#6938EF]">{active.action.replace(/_/g, " ")}</span>
                  {" · "}{active.pos_profile}
                </p>
                {(() => {
                  let items: DiscountItem[] = [];
                  try { items = active.meta ? JSON.parse(active.meta) : []; } catch { /* ignore */ }
                  return items.length > 0 ? (
                    <div className="mb-3 rounded-lg bg-amber-50 px-3 py-2">
                      <p className="mb-1 text-[10px] font-semibold text-amber-700">Items & discounts</p>
                      <ul className="space-y-0.5">
                        {items.map((d) => (
                          <li key={d.item_name} className="flex items-center justify-between text-[11px] text-amber-800">
                            <span className="truncate max-w-40">{d.item_name}</span>
                            <span className="ml-2 font-bold shrink-0">{d.pct.toFixed(1)}%</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null;
                })()}
                <label className="mb-1.5 block text-xs font-semibold text-[#212B36]">
                  Your PIN ({accessLevel})
                </label>
                <input
                  ref={pinRef}
                  type="password"
                  inputMode="numeric"
                  maxLength={8}
                  value={pin}
                  onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
                  placeholder="Enter PIN"
                  className="mb-3 w-full rounded-lg border border-[#E6EAED] px-3 py-2 text-sm text-[#212B36] outline-none focus:border-[#6938EF]"
                  onKeyDown={(e) => { if (e.key === "Enter") respond("approve"); }}
                />
                {error && <p className="mb-3 text-xs text-red-500">{error}</p>}
                <div className="flex gap-2">
                  <button type="button" disabled={submitting || pin.length < 4} onClick={() => respond("deny")}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-red-200 py-2 text-xs font-semibold text-red-600 disabled:opacity-40 hover:bg-red-50">
                    <XCircle className="h-3.5 w-3.5" />Deny
                  </button>
                  <button type="button" disabled={submitting || pin.length < 4} onClick={() => respond("approve")}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#6938EF] py-2 text-xs font-bold text-white disabled:opacity-40 hover:bg-[#5a2fd6]">
                    {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                    Approve
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

