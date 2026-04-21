import { useState, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, post } from "@/lib/api";
import { clearSession } from "@/lib/session";
import { PinPad } from "@/components/pos/PinPad";
import { Loader2, Lock, AlertCircle, ChevronLeft, ShieldCheck, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Cashier, POSProfile } from "@/types/pos";

interface Props {
  profile: POSProfile;
  onLogin: (cashier: Cashier) => void;
  onChangeProfile: () => void;
}

type Screen =
  | { type: "picker" }
  | { type: "pin"; cashier: Cashier }
  | { type: "supervisor_pick"; lockedCashier: Cashier }
  | { type: "supervisor_pin"; lockedCashier: Cashier; supervisor: Cashier };

interface VerifyResponse {
  status: "ok" | "wrong_pin" | "locked" | "no_pin" | "invalid";
  full_name?: string;
  access_level?: string;
  attempts_left?: number;
  lockout_until?: string;
  message?: string;
}

interface OverrideResponse {
  status: "ok" | "forbidden" | "locked" | "wrong_pin" | "no_pin" | "invalid";
  message?: string;
  lockout_until?: string;
}

interface ForgotPinResponse {
  status: "ok" | "error";
  message?: string;
}

type ForgotPhase = "idle" | "confirming" | "done" | "error";

function maskEmail(email: string): string {
  const at = email.indexOf("@");
  if (at <= 0) return "your registered email";
  return `${email[0]}****${email.slice(at)}`;
}

function useCountdown(until: string | null | undefined): string {
  const [display, setDisplay] = useState("");
  useEffect(() => {
    if (!until) { setDisplay(""); return; }
    const tick = () => {
      const diff = Math.max(0, new Date(until).getTime() - Date.now());
      if (diff === 0) { setDisplay(""); return; }
      const m = Math.floor(diff / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setDisplay(`${m}:${s.toString().padStart(2, "0")}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [until]);
  return display;
}

// ── Shared split-panel wrapper ───────────────────────────────────────────────
function SplitPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex items-center justify-center p-5 bg-[#f0f0f0]">
      <div className="flex w-full max-w-245 min-h-165 xl:max-w-290 xl:min-h-185 2xl:max-w-325 2xl:min-h-205 rounded-xl overflow-hidden shadow-[0_8px_40px_rgba(0,0,0,.14)]">

        {/* Left: form panel */}
        <div className="w-105 xl:w-125 2xl:w-140 shrink-0 bg-white flex flex-col justify-between p-9 xl:p-12 2xl:p-16 max-[860px]:w-90 max-[860px]:p-7 max-[640px]:w-full max-[640px]:min-h-dvh overflow-y-auto">
          {children}
        </div>

        {/* Right: image */}
        <div className="flex-1 relative bg-[#1a1a2e] hidden min-[640px]:block">
          <img
            src="/assets/surge/images/Rectangle 3411.png"
            alt="POS terminal"
            className="absolute inset-0 w-full h-full object-cover object-center"
            onError={(e) => (e.currentTarget.style.display = "none")}
          />
        </div>

      </div>
    </div>
  );
}

// Logo strip reused across all states
function PanelLogo() {
  return (
    <div className="flex items-center gap-2.5">
      <img
        src="/assets/surge/images/SurgeLogo.png"
        alt="Surge POS"
        className="w-10 h-10 object-contain"
        onError={(e) => (e.currentTarget.style.display = "none")}
      />
      <span className="text-[22px] font-extrabold tracking-tight text-[#212b36]">
        Surge <span className="text-[#6366f1]">POS</span>
      </span>
    </div>
  );
}

function PanelFooter({
  onBack,
  backLabel,
  onLogout,
}: {
  onBack?: () => void;
  backLabel?: string;
  onLogout?: () => void;
}) {
  return (
    <div className="flex items-center justify-between pt-5 border-t border-[#f4f6f8]">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1 text-xs font-semibold text-[#919eab] hover:text-[#6366f1] tracking-wide transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          {backLabel ?? "Back"}
        </button>
      ) : (
        <span />
      )}
      <div className="flex items-center gap-4">
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center gap-1 text-xs font-semibold text-[#919eab] hover:text-red-500 tracking-wide transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Log out
          </button>
        )}
        <span className="text-xs text-[#919eab]">Copyrights © 2025 – Surge POS</span>
      </div>
    </div>
  );
}

// ── Cashier avatar card (for picker grid) ────────────────────────────────────
function CashierCard({ cashier, onSelect }: { cashier: Cashier; onSelect: (c: Cashier) => void }) {
  const countdown = useCountdown(cashier.lockout_until);
  const isLocked = cashier.locked;
  const noPin = !cashier.has_pin;

  return (
    <button
      type="button"
      onClick={() => onSelect(cashier)}
      className={cn(
        "relative flex flex-col items-center gap-2 rounded-xl border p-3.5 transition-all",
        "hover:border-[#6366f1]/40 hover:bg-[#f5f5ff] active:scale-[.98]",
        isLocked && "border-red-200 bg-red-50",
        noPin    && "border-amber-200 bg-amber-50",
        !isLocked && !noPin && "border-[#dfe3e8] bg-white",
      )}
    >
      {cashier.user_image ? (
        <img src={cashier.user_image} alt={cashier.full_name} className="h-12 w-12 rounded-full object-cover" />
      ) : (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#6366f1]/10 text-xl font-bold text-[#6366f1]">
          {cashier.full_name[0]?.toUpperCase() ?? "?"}
        </div>
      )}

      {isLocked && (
        <span className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white">
          <Lock className="h-3 w-3" />
        </span>
      )}
      {noPin && !isLocked && (
        <span className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-white">
          <AlertCircle className="h-3 w-3" />
        </span>
      )}

      <span className="max-w-full truncate text-[13px] font-semibold text-[#212b36]">{cashier.full_name}</span>
      {isLocked && (
        <span className="text-[11px] text-red-500">{countdown ? `Locked · ${countdown}` : "Locked"}</span>
      )}
      {noPin && !isLocked && (
        <span className="text-[11px] text-amber-500">PIN not set</span>
      )}
    </button>
  );
}

// ── Main component ───────────────────────────────────────────────────────────
export function CashierScreen({ profile, onLogin, onChangeProfile }: Props) {
  const qc = useQueryClient();
  const [screen, setScreen] = useState<Screen>({ type: "picker" });
  const [pinErrorCount, setPinErrorCount] = useState(0);
  const [pinMessage, setPinMessage] = useState<string | undefined>();
  const [pinMessageType, setPinMessageType] = useState<"error" | "warning" | "info">("error");
  const [forgotPhase, setForgotPhase] = useState<ForgotPhase>("idle");
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  async function confirmLogout() {
    setLoggingOut(true);
    try {
      clearSession();
      await post("logout");
    } catch {
      // logout endpoint may not return clean JSON — redirect anyway
    }
    window.location.href = "/surge";
  }

  const cashiersQ = useQuery({
    queryKey: ["cashiers", profile.name],
    queryFn: () =>
      api.get<{ cashiers: Cashier[] }>("surge.api.auth.get_cashiers", { pos_profile: profile.name }),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });

  const cashiers = cashiersQ.data?.cashiers ?? [];

  const verifyMutation = useMutation({
    mutationFn: ({ user, pin }: { user: string; pin: string }) =>
      api.post<VerifyResponse>("surge.api.auth.verify_pin", {
        pos_profile: profile.name,
        user,
        pin,
      }),
  });

  const overrideMutation = useMutation({
    mutationFn: ({ supervisorPin, lockedUser }: { supervisorPin: string; lockedUser: string }) =>
      api.post<OverrideResponse>("surge.api.auth.override_lockout", {
        pos_profile: profile.name,
        locked_user: lockedUser,
        supervisor_pin: supervisorPin,
      }),
  });

  const forgotPinMutation = useMutation({
    mutationFn: (user: string) =>
      api.post<ForgotPinResponse>("surge.api.auth.forgot_pin", {
        pos_profile: profile.name,
        user,
      }),
  });

  const handleCashierSelect = useCallback((cashier: Cashier) => {
    setForgotPhase("idle");
    setPinErrorCount(0);
    if (!cashier.has_pin) {
      setPinMessage("PIN not configured. Ask your manager to set a PIN.");
      setPinMessageType("info");
    } else {
      setPinMessage(undefined);
    }
    setScreen({ type: "pin", cashier });
  }, []);

  // Auto-advance to PIN when only one Active cashier on the profile
  useEffect(() => {
    if (screen.type === "picker" && cashiers.length === 1) {
      handleCashierSelect(cashiers[0]!);
    }
  }, [cashiers.length, screen.type, handleCashierSelect]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePinSubmit = useCallback(
    async (pin: string) => {
      if (screen.type !== "pin") return;
      const { cashier } = screen;
      if (!cashier.has_pin) return;

      const pinHash = await api.hashPin(pin);
      const result = await verifyMutation.mutateAsync({ user: cashier.user, pin: pinHash });

      if (result.status === "ok") {
        const loggedIn: Cashier = {
          ...cashier,
          access_level: (result.access_level as Cashier["access_level"]) ?? cashier.access_level,
        };
        onLogin(loggedIn);
        return;
      }
      if (result.status === "wrong_pin") {
        const left = result.attempts_left ?? 0;
        setPinMessage(left === 1 ? "Wrong PIN. 1 attempt left." : `Wrong PIN. ${left} attempts left.`);
        setPinMessageType("error");
        setPinErrorCount((c) => c + 1);
        return;
      }
      if (result.status === "locked") {
        qc.invalidateQueries({ queryKey: ["cashiers", profile.name] });
        setScreen({ type: "picker" });
        return;
      }
      if (result.status === "no_pin") {
        setPinMessage("PIN not configured. Ask your manager to set a PIN.");
        setPinMessageType("info");
        setPinErrorCount((c) => c + 1);
        return;
      }
      setPinMessage(result.message ?? "Invalid PIN.");
      setPinMessageType("error");
      setPinErrorCount((c) => c + 1);
    },
    [screen, verifyMutation, qc, profile.name, onLogin],
  );

  const handleSupervisorPinSubmit = useCallback(
    async (pin: string) => {
      if (screen.type !== "supervisor_pin") return;
      const { lockedCashier } = screen;

      const pinHash = await api.hashPin(pin);
      const result = await overrideMutation.mutateAsync({
        supervisorPin: pinHash,
        lockedUser: lockedCashier.user,
      });

      if (result.status === "ok") {
        qc.invalidateQueries({ queryKey: ["cashiers", profile.name] });
        setScreen({ type: "picker" });
        return;
      }
      if (result.status === "locked") {
        setPinMessage("Your account is locked. Cannot override.");
        setPinMessageType("error");
        setPinErrorCount((c) => c + 1);
        return;
      }
      if (result.status === "wrong_pin") {
        const left = (result as { attempts_left?: number }).attempts_left;
        setPinMessage(left != null ? `Wrong PIN. ${left} attempts left.` : "Wrong PIN.");
        setPinMessageType("error");
        setPinErrorCount((c) => c + 1);
        return;
      }
      if (result.status === "forbidden") {
        setPinMessage("Only Supervisors and Managers can override lockouts.");
        setPinMessageType("error");
        setPinErrorCount((c) => c + 1);
        return;
      }
      setPinMessage(result.message ?? "Override failed.");
      setPinMessageType("error");
      setPinErrorCount((c) => c + 1);
    },
    [screen, overrideMutation, qc, profile.name],
  );

  const handleForgotPinSend = useCallback(async () => {
    if (screen.type !== "pin") return;
    setForgotPhase("confirming"); // skip — go straight to sending on this call
    try {
      const result = await forgotPinMutation.mutateAsync(screen.cashier.user);
      setForgotPhase(result.status === "ok" ? "done" : "error");
    } catch {
      setForgotPhase("error");
    }
  }, [screen, forgotPinMutation]);

  // ── Loading ──
  if (cashiersQ.isLoading) {
    return (
      <SplitPanel>
        <PanelLogo />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#6366f1]" />
        </div>
        <PanelFooter />
      </SplitPanel>
    );
  }

  // ── API Error ──
  if (cashiersQ.error) {
    return (
      <SplitPanel>
        <PanelLogo />
        <div className="flex flex-1 flex-col items-center justify-center gap-4">
          <AlertCircle className="h-8 w-8 text-red-500" />
          <p className="text-sm text-[#637381] text-center">
            {(cashiersQ.error as Error).message}
          </p>
          <button
            type="button"
            onClick={() => cashiersQ.refetch()}
            className="text-sm font-semibold text-[#6366f1] hover:underline"
          >
            Try again
          </button>
        </div>
        <PanelFooter onBack={onChangeProfile} backLabel="Change profile" />
      </SplitPanel>
    );
  }

  const supervisors = cashiers.filter(
    (c) => c.access_level === "Supervisor" || c.access_level === "Manager",
  );

  // ── Picker ──
  if (screen.type === "picker") {
    return (
      <>
        <SplitPanel>
          <PanelLogo />
          <div className="flex flex-col gap-5 py-6">
            <div>
              <h1 className="text-[26px] font-bold leading-tight text-[#212b36] mb-1">
                Who's at the register?
              </h1>
              <p className="text-sm text-[#637381]">{profile.name}</p>
            </div>

            {cashiers.length === 0 ? (
              <p className="text-sm text-[#637381]">
                No cashiers assigned to this profile. Contact your administrator.
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {cashiers.map((c) => (
                  <CashierCard key={c.user} cashier={c} onSelect={handleCashierSelect} />
                ))}
              </div>
            )}
          </div>
          <PanelFooter
            onBack={onChangeProfile}
            backLabel="Change profile"
            onLogout={() => setLogoutConfirmOpen(true)}
          />
        </SplitPanel>

        {/* ── Logout confirmation modal ── */}
        {logoutConfirmOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="mx-4 w-full max-w-sm rounded-2xl border border-[#dfe3e8] bg-white p-6 shadow-2xl">
              <div className="mb-1 flex items-center gap-2">
                <LogOut className="h-4 w-4 text-red-500" />
                <h2 className="text-base font-bold text-[#212b36]">Log out terminal?</h2>
              </div>
              <p className="mb-5 text-sm text-[#637381]">
                This ends the terminal session. The next user will need to sign in
                with their Frappe credentials to continue.
              </p>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setLogoutConfirmOpen(false)}
                  disabled={loggingOut}
                  className="rounded-lg border border-[#dfe3e8] px-4 py-2 text-sm font-medium text-[#637381] hover:bg-[#f4f6f8] disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => void confirmLogout()}
                  disabled={loggingOut}
                  className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-60"
                >
                  {loggingOut
                    ? <><Loader2 className="h-3 w-3 animate-spin" /> Logging out…</>
                    : <><LogOut className="h-3 w-3" /> Log out</>
                  }
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  // ── PIN entry ──
  if (screen.type === "pin") {
    const { cashier } = screen;
    const isLocked = cashier.locked;

    return (
      <SplitPanel>
        <PanelLogo />

        <div className="flex flex-col items-center gap-5 py-4">
          {/* Cashier identity */}
          <div className="flex flex-col items-center gap-2">
            {cashier.user_image ? (
              <img
                src={cashier.user_image}
                alt={cashier.full_name}
                className="h-16 w-16 rounded-full object-cover ring-2 ring-[#6366f1]/20"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#6366f1]/10 text-2xl font-bold text-[#6366f1]">
                {cashier.full_name[0]?.toUpperCase() ?? "?"}
              </div>
            )}
            <p className="text-lg font-bold text-[#212b36]">{cashier.full_name}</p>
            <span className="rounded-full bg-[#6366f1]/10 px-2.5 py-0.5 text-[11px] font-semibold text-[#6366f1] uppercase tracking-wide">
              {cashier.access_level}
            </span>
          </div>

          <div className="text-center">
            <h1 className="text-[22px] font-bold text-[#212b36] mb-0.5">PIN Verification</h1>
            <p className="text-sm text-[#637381]">Enter your PIN to sign in</p>
          </div>

          {/* Locked state */}
          {isLocked ? (
            <div className="flex flex-col items-center gap-4 w-full">
              <div className="flex items-center gap-2 rounded-md bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-600">
                <Lock className="h-4 w-4 shrink-0" />
                Account temporarily locked due to too many incorrect attempts.
              </div>
              {supervisors.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setPinErrorCount(0);
                    setPinMessage(undefined);
                    setScreen({ type: "supervisor_pick", lockedCashier: cashier });
                  }}
                  className="flex items-center gap-2 rounded-lg border border-[#6366f1]/40 px-4 py-2 text-sm font-semibold text-[#6366f1] hover:bg-[#6366f1]/5 transition-colors"
                >
                  <ShieldCheck className="h-4 w-4" />
                  Request supervisor override
                </button>
              )}
            </div>
          ) : (
            <>
              <PinPad
                onSubmit={handlePinSubmit}
                disabled={!cashier.has_pin}
                errorCount={pinErrorCount}
                message={pinMessage}
                messageType={pinMessageType}
              />

              {/* Forgot PIN */}
              <div className="w-full text-center mt-1">
                {forgotPhase === "idle" && (
                  <button
                    type="button"
                    onClick={() => setForgotPhase("confirming")}
                    className="text-sm text-[#919eab] hover:text-[#6366f1] transition-colors"
                  >
                    Forgot your PIN?
                  </button>
                )}

                {forgotPhase === "confirming" && (
                  <div className="rounded-lg border border-[#dfe3e8] bg-[#f8f9fa] p-3 text-left">
                    <p className="text-[13px] text-[#212b36] font-medium mb-1">Request PIN reset?</p>
                    <p className="text-xs text-[#637381] mb-3">
                      An email will be sent to{" "}
                      <span className="font-semibold text-[#454f5b]">{maskEmail(cashier.user)}</span>{" "}
                      and your manager will be notified.
                    </p>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void handleForgotPinSend()}
                        disabled={forgotPinMutation.isPending}
                        className="flex-1 h-8 bg-[#6366f1] hover:bg-[#4f46e5] disabled:opacity-55 text-white text-xs font-bold rounded-md transition-colors"
                      >
                        {forgotPinMutation.isPending ? "Sending…" : "Send Reset Request"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setForgotPhase("idle")}
                        className="flex-1 h-8 bg-white border border-[#dfe3e8] hover:bg-[#f0f0f0] text-xs font-semibold text-[#454f5b] rounded-md transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {forgotPhase === "done" && (
                  <p className="text-[13px] text-green-600 font-medium">
                    Reset request sent. Check your email and contact your manager.
                  </p>
                )}

                {forgotPhase === "error" && (
                  <p className="text-[13px] text-red-500 font-medium">
                    Could not send reset request. Try again or contact your manager.
                  </p>
                )}
              </div>
            </>
          )}
        </div>

        <PanelFooter onBack={() => setScreen({ type: "picker" })} backLabel="Back to cashiers" />
      </SplitPanel>
    );
  }

  // ── Supervisor picker ──
  if (screen.type === "supervisor_pick") {
    const { lockedCashier } = screen;
    return (
      <SplitPanel>
        <PanelLogo />

        <div className="flex flex-col items-center gap-5 py-4">
          <ShieldCheck className="h-10 w-10 text-[#6366f1]" />
          <div className="text-center">
            <h1 className="text-[22px] font-bold text-[#212b36] mb-1">Supervisor Override</h1>
            <p className="text-sm text-[#637381]">
              Select a supervisor to unlock{" "}
              <span className="font-semibold text-[#212b36]">{lockedCashier.full_name}</span>
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 w-full">
            {supervisors.map((s) => (
              <CashierCard
                key={s.user}
                cashier={s}
                onSelect={(supervisor) => {
                  setPinErrorCount(0);
                  setPinMessage(undefined);
                  setScreen({ type: "supervisor_pin", lockedCashier, supervisor });
                }}
              />
            ))}
          </div>
        </div>

        <PanelFooter
          onBack={() => setScreen({ type: "pin", cashier: lockedCashier })}
          backLabel="Back"
        />
      </SplitPanel>
    );
  }

  // ── Supervisor PIN ──
  if (screen.type === "supervisor_pin") {
    const { lockedCashier, supervisor } = screen;
    return (
      <SplitPanel>
        <PanelLogo />

        <div className="flex flex-col items-center gap-5 py-4">
          <div className="flex flex-col items-center gap-2">
            {supervisor.user_image ? (
              <img
                src={supervisor.user_image}
                alt={supervisor.full_name}
                className="h-16 w-16 rounded-full object-cover ring-2 ring-[#6366f1]/20"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#6366f1]/10 text-2xl font-bold text-[#6366f1]">
                {supervisor.full_name[0]?.toUpperCase() ?? "?"}
              </div>
            )}
            <p className="text-lg font-bold text-[#212b36]">{supervisor.full_name}</p>
            <span className="rounded-full bg-[#6366f1]/10 px-2.5 py-0.5 text-[11px] font-semibold text-[#6366f1] uppercase tracking-wide">
              {supervisor.access_level}
            </span>
          </div>

          <div className="text-center">
            <h1 className="text-[22px] font-bold text-[#212b36] mb-0.5">Supervisor Override</h1>
            <p className="text-sm text-[#637381]">
              Enter your PIN to unlock{" "}
              <span className="font-semibold text-[#212b36]">{lockedCashier.full_name}</span>
            </p>
          </div>

          <PinPad
            onSubmit={handleSupervisorPinSubmit}
            errorCount={pinErrorCount}
            message={pinMessage}
            messageType={pinMessageType}
          />
        </div>

        <PanelFooter
          onBack={() => setScreen({ type: "supervisor_pick", lockedCashier })}
          backLabel="Back"
        />
      </SplitPanel>
    );
  }

  return null;
}
