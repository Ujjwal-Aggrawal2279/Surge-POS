import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { X, Loader2, ShieldCheck, Clock, XCircle, Hourglass, WifiOff } from "lucide-react";
import { get, post } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Cashier } from "@/types/pos";

interface CashiersResponse { cashiers: Cashier[] }
interface DiscountItem { item_name: string; pct: number }

interface Props {
  posProfile: string;
  action: string;
  discountItems?: DiscountItem[];
  onApproved: (token: string, approver: Cashier) => void;
  onClose: () => void;
}

type Stage = "select" | "waiting" | "unanswered" | "denied" | "expired" | "unavailable";
const TIMEOUT_SEC = 180; // 3-min display timer; request lives 30 min in Redis
const SS_KEY = "surge:pending_approval"; // sessionStorage key for page-refresh resilience

export function ManagerApprovalModal({ posProfile, action, discountItems, onApproved, onClose }: Props) {
  // Restore pending request from sessionStorage (survives page refresh)
  const [stage, setStage]             = useState<Stage>(() => {
    try {
      const saved = sessionStorage.getItem(SS_KEY);
      if (saved) return "waiting";
    } catch { /* sessionStorage unavailable */ }
    return "select";
  });
  const [selected, setSelected]       = useState<Cashier | null>(null);
  const [reqId, setReqId]             = useState<string>(() => {
    try {
      const saved = sessionStorage.getItem(SS_KEY);
      if (saved) return JSON.parse(saved).reqId ?? "";
    } catch { /* ignore */ }
    return "";
  });
  const [sending, setSending]         = useState(false);
  const [error, setError]             = useState("");
  const [secondsLeft, setSecondsLeft] = useState(TIMEOUT_SEC);
  const pollRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["cashiers", posProfile],
    queryFn: () => get<CashiersResponse>("surge.api.auth.get_cashiers", { pos_profile: posProfile }),
    staleTime: 30_000,
  });
  const approvers = (data?.cashiers ?? []).filter((c) => c.access_level !== "Cashier");

  function clearIntervals() {
    if (pollRef.current)  clearInterval(pollRef.current);
    if (timerRef.current) clearInterval(timerRef.current);
  }

  function clearSession() {
    try { sessionStorage.removeItem(SS_KEY); } catch { /* ignore */ }
  }

  const cancelRequest = useCallback(async (id: string) => {
    clearIntervals();
    clearSession();
    if (!id) return;
    try {
      await post("surge.api.auth.cancel_approval_request", { req_id: id });
    } catch { /* best-effort — Redis TTL will clean up */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleResponse(d: { status?: string; token?: string; approver_name?: string; message?: string }) {
    clearIntervals();
    clearSession();
    if (d.status === "approved" && d.token && selected) {
      onApproved(d.token, { ...selected, full_name: d.approver_name ?? selected.full_name });
    } else if (d.status === "denied") {
      setError(d.message ?? "Request denied.");
      setStage("denied");
    } else if (d.status === "expired") {
      setStage("expired");
    }
  }

  useEffect(() => {
    if ((stage !== "waiting" && stage !== "unanswered") || !reqId) return;
    const cb = (ev: unknown) => {
      const d = ev as { req_id?: string; status?: string; token?: string; approver_name?: string; message?: string };
      if (d.req_id === reqId) handleResponse(d);
    };
    const rt = window.frappe?.realtime;
    rt?.on("surge:approval_response", cb);
    return () => rt?.off("surge:approval_response", cb);
  }, [stage, reqId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if ((stage !== "waiting" && stage !== "unanswered") || !reqId) return;
    pollRef.current = setInterval(async () => {
      try {
        const res = await get<{ status: string; token?: string; approver_name?: string; message?: string }>(
          "surge.api.auth.poll_approval", { req_id: reqId },
        );
        if (res.status !== "pending") handleResponse(res);
      } catch { /* keep polling */ }
    }, 3_000);
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          setStage("unanswered"); // poll keeps running — manager may still approve
          return 0;
        }
        return s - 1;
      });
    }, 1_000);
    return clearIntervals;
  }, [stage, reqId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function sendRequest() {
    if (!selected) return;
    setSending(true);
    setError("");
    try {
      const meta = discountItems?.length
        ? JSON.stringify(discountItems.map((d) => ({ item_name: d.item_name, pct: d.pct })))
        : "";
      const res = await post<{ status: string; req_id?: string; message?: string }>(
        "surge.api.auth.request_approval_remote",
        { pos_profile: posProfile, approver: selected.user, action, meta },
      );
      if (res.status === "pending" && res.req_id) {
        try {
          sessionStorage.setItem(SS_KEY, JSON.stringify({ reqId: res.req_id, approver: selected?.user }));
        } catch { /* sessionStorage full or unavailable */ }
        setReqId(res.req_id);
        setSecondsLeft(TIMEOUT_SEC);
        setStage("waiting");
      } else if (res.status === "redis_unavailable") {
        setStage("unavailable");
      } else {
        setError(res.message ?? "Failed to send request.");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSending(false);
    }
  }

  const mins = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const secs = String(secondsLeft % 60).padStart(2, "0");

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-[#6938EF]" />
            <h2 className="text-base font-bold text-[#212B36]">Manager Approval</h2>
          </div>
          <button
            type="button"
            title="Close"
            onClick={async () => {
              if (reqId && (stage === "waiting" || stage === "unanswered")) {
                await cancelRequest(reqId);
              }
              onClose();
            }}
            className="text-[#646B72] hover:text-[#212B36]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {stage === "select" && (
          <>
            {discountItems && discountItems.length > 0 && (
              <div className="mb-4 rounded-lg bg-amber-50 px-3 py-2.5">
                <p className="mb-1.5 text-xs font-semibold text-amber-700">Discounts requiring approval</p>
                <ul className="space-y-0.5">
                  {discountItems.map((d) => (
                    <li key={d.item_name} className="flex items-center justify-between text-xs text-amber-800">
                      <span className="truncate max-w-50">{d.item_name}</span>
                      <span className="ml-2 font-bold shrink-0">{d.pct.toFixed(1)}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="mb-4 text-sm text-[#646B72]">
              Select an approver. They will receive a request on their screen.
            </p>
            {isLoading ? (
              <div className="flex justify-center py-6"><Loader2 className="h-6 w-6 animate-spin text-[#6938EF]" /></div>
            ) : approvers.length === 0 ? (
              <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
                No Supervisors or Managers configured on this profile.
              </p>
            ) : (
              <div className="mb-4 flex flex-col gap-1.5">
                {approvers.map((a) => (
                  <button key={a.user} type="button" onClick={() => setSelected(a)}
                    className={cn(
                      "flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors",
                      selected?.user === a.user
                        ? "border-[#6938EF] bg-[#F4F3FF] font-semibold text-[#6938EF]"
                        : "border-[#E6EAED] text-[#212B36] hover:border-[#6938EF]/40",
                    )}>
                    <span className="flex-1 text-left">{a.full_name}</span>
                    <span className={cn("rounded px-1.5 py-0.5 text-xs",
                      a.access_level === "Manager" ? "bg-[#6938EF] text-white" : "bg-[#E6EAED] text-[#646B72]",
                    )}>{a.access_level}</span>
                  </button>
                ))}
              </div>
            )}
            {error && <p className="mb-3 text-sm text-red-500">{error}</p>}
            <button type="button" disabled={!selected || sending} onClick={sendRequest}
              className="flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-[#6938EF] text-sm font-bold text-white disabled:opacity-40 hover:bg-[#5a2fd6]">
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              {sending ? "Sending…" : "Send Approval Request"}
            </button>
          </>
        )}

        {stage === "waiting" && selected && (
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#F4F3FF]">
              <Loader2 className="h-10 w-10 animate-spin text-[#6938EF]" />
            </div>
            <div>
              <p className="text-base font-bold text-[#212B36]">Waiting for {selected.full_name}</p>
              <p className="mt-0.5 text-xs text-[#919EAB]">Request sent to their screen</p>
            </div>
            <div className="flex items-center gap-1.5 rounded-full bg-[#F4F3FF] px-4 py-1.5 text-sm font-semibold text-[#6938EF]">
              <Clock className="h-3.5 w-3.5" />{mins}:{secs}
            </div>
            <button type="button" onClick={async () => { await cancelRequest(reqId); setStage("select"); setReqId(""); }}
              className="text-xs text-[#919EAB] underline-offset-2 hover:underline">
              Cancel request
            </button>
          </div>
        )}

        {stage === "denied" && (
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-50">
              <XCircle className="h-9 w-9 text-red-500" />
            </div>
            <div>
              <p className="text-base font-bold text-[#212B36]">Request Denied</p>
              <p className="mt-0.5 text-sm text-[#646B72]">{error}</p>
            </div>
            <button type="button" onClick={() => { setStage("select"); setError(""); setReqId(""); }}
              className="h-9 rounded-xl border border-[#E6EAED] px-4 text-sm font-semibold text-[#212B36] hover:bg-[#F4F6F8]">
              Try again
            </button>
          </div>
        )}

        {stage === "unanswered" && selected && (
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-amber-50">
              <Hourglass className="h-10 w-10 text-amber-500" />
            </div>
            <div>
              <p className="text-base font-bold text-[#212B36]">{selected.full_name} hasn't responded yet</p>
              <p className="mt-1 text-xs text-[#919EAB]">
                The request is still active for 30 minutes.<br />
                They'll see it when they open Surge or log in.
              </p>
            </div>
            <div className="flex items-center gap-1.5 rounded-full bg-amber-50 px-4 py-1.5 text-xs font-semibold text-amber-600">
              <Loader2 className="h-3 w-3 animate-spin" />
              Still checking every 3 seconds…
            </div>
            <button type="button" onClick={async () => { await cancelRequest(reqId); setStage("select"); setReqId(""); }}
              className="text-xs text-[#919EAB] underline-offset-2 hover:underline">
              Cancel and choose someone else
            </button>
          </div>
        )}

        {stage === "unavailable" && (
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
              <WifiOff className="h-9 w-9 text-amber-500" />
            </div>
            <div>
              <p className="text-base font-bold text-[#212B36]">Remote approval unavailable</p>
              <p className="mt-1 text-sm text-[#646B72]">
                Ask the manager to come to this terminal and enter their PIN directly.
              </p>
            </div>
            <button type="button" onClick={() => setStage("select")}
              className="h-9 rounded-xl border border-[#E6EAED] px-4 text-sm font-semibold text-[#212B36] hover:bg-[#F4F6F8]">
              Try again
            </button>
          </div>
        )}

        {stage === "expired" && (
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
              <Clock className="h-9 w-9 text-amber-500" />
            </div>
            <div>
              <p className="text-base font-bold text-[#212B36]">Request Expired</p>
              <p className="mt-0.5 text-sm text-[#646B72]">This request has expired. Send a new one.</p>
            </div>
            <button type="button" onClick={() => { setStage("select"); setReqId(""); }}
              className="h-9 rounded-xl border border-[#E6EAED] px-4 text-sm font-semibold text-[#212B36] hover:bg-[#F4F6F8]">
              Send again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
