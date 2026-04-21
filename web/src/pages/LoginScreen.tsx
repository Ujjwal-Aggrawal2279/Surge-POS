import { useActionState, useEffect, useState } from "react";
import { Eye, EyeOff, Mail } from "lucide-react";

const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;

interface LoginResponse {
  message?: string;
  home_page?: string;
  _server_messages?: string;
}

type FormState =
  | null
  | { kind: "field"; field: "usr" | "pwd" | "otp"; msg: string }
  | { kind: "alert"; type: "warning" | "info"; msg: string }
  | { kind: "otp"; infoMsg: string };

function extractMessage(json: LoginResponse): string | null {
  if (json.message && json.message !== "Logged In") return json.message;
  if (json._server_messages) {
    try {
      const msgs = JSON.parse(json._server_messages) as string[];
      const raw = msgs[0];
      if (raw) {
        const first = JSON.parse(raw) as { message?: string };
        if (first.message) return first.message;
      }
    } catch { /* malformed */ }
  }
  return null;
}

async function loginAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const usr = (formData.get("usr") as string | null)?.trim() ?? "";
  const pwd = (formData.get("pwd") as string | null) ?? "";
  const otp = (formData.get("otp") as string | null)?.trim() ?? "";

  if (!usr) return { kind: "field", field: "usr", msg: "Email is required." };
  if (!EMAIL_RE.test(usr)) return { kind: "field", field: "usr", msg: "Enter a valid email address." };
  if (!pwd) return { kind: "field", field: "pwd", msg: "Password is required." };

  if (!navigator.onLine)
    return { kind: "alert", type: "warning", msg: "Cannot reach server. Check your network." };

  let res: Response;
  let json: LoginResponse;
  try {
    const body = new URLSearchParams({ usr, pwd, cmd: "login" });
    if (otp) body.set("otp", otp);
    res = await fetch("/api/method/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
  } catch {
    return { kind: "alert", type: "warning", msg: "Cannot reach server. Check your network." };
  }
  try { json = (await res.json()) as LoginResponse; } catch { json = {}; }

  if (res.ok && (json.message === "Logged In" || json.home_page)) {
    window.location.reload();
    return null;
  }

  const msg = json.message?.toLowerCase() ?? "";

  if (res.status === 200 && (msg.includes("verification") || msg.includes("otp") || msg.includes("two factor")))
    return { kind: "otp", infoMsg: json.message ?? "Enter the one-time code sent to your device." };

  if (res.status === 200 && msg.includes("update password")) {
    window.location.href = "/update-password";
    return null;
  }

  if (res.status === 401 || res.status === 403) {
    const text = extractMessage(json) ?? "Incorrect email or password.";
    const lower = text.toLowerCase();
    if (lower.includes("disabled") || lower.includes("blocked"))
      return { kind: "field", field: "pwd", msg: "This account has been disabled. Contact your administrator." };
    if (lower.includes("locked"))
      return { kind: "field", field: "pwd", msg: "Account temporarily locked. Try again later." };
    return { kind: "field", field: "pwd", msg: text };
  }

  if (res.status === 429)
    return { kind: "alert", type: "warning", msg: "Too many attempts. Wait a few minutes and try again." };
  if (res.status >= 500)
    return { kind: "field", field: "pwd", msg: "Server error. Please try again in a moment." };

  return { kind: "field", field: "pwd", msg: extractMessage(json) ?? "Sign in failed. Please try again." };
}

export function LoginScreen() {
  const [state, formAction, isPending] = useActionState<FormState, FormData>(loginAction, null);
  const [networkLost, setNetworkLost] = useState(false);

  useEffect(() => {
    const down = () => setNetworkLost(true);
    const up   = () => setNetworkLost(false);
    window.addEventListener("offline", down);
    window.addEventListener("online",  up);
    return () => {
      window.removeEventListener("offline", down);
      window.removeEventListener("online",  up);
    };
  }, []);

  const showOtp = state?.kind === "otp";

  const usrError = state?.kind === "field" && state.field === "usr" ? state.msg : null;
  const pwdError = state?.kind === "field" && state.field === "pwd" ? state.msg : null;
  const otpError = state?.kind === "field" && state.field === "otp" ? state.msg : null;

  const alert = state?.kind === "alert"
    ? state
    : state?.kind === "otp"
      ? { type: "info" as const, msg: state.infoMsg }
      : null;

  const ALERT_CLS = {
    warning: "bg-amber-50 border border-amber-200 text-amber-700",
    info:    "bg-blue-50 border border-blue-200 text-blue-700",
  } as const;

  return (
    <div className="min-h-dvh flex items-center justify-center p-5 bg-[#f0f0f0]">
      <div className="flex w-full max-w-245 min-h-165 xl:max-w-290 xl:min-h-185 2xl:max-w-325 2xl:min-h-205 rounded-xl overflow-hidden shadow-[0_8px_40px_rgba(0,0,0,.14)]">

        <div className="w-105 xl:w-125 2xl:w-140 shrink-0 bg-white flex flex-col justify-between p-9 xl:p-12 2xl:p-16 max-[860px]:w-90 max-[860px]:p-7 max-[640px]:w-full max-[640px]:min-h-dvh">

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

          <div className="flex flex-col gap-[18px] py-8">

            <div>
              <h1 className="text-[26px] font-bold leading-tight text-[#212b36] mb-1">Sign In</h1>
              <p className="text-sm text-[#637381] leading-relaxed">
                Access the Surge POS terminal using your email and passcode.
              </p>
            </div>

            {networkLost && (
              <div className="rounded-md px-3 py-2 text-[13px] bg-amber-50 border border-amber-200 text-amber-700" role="alert">
                Connection lost. Check your network and try again.
              </div>
            )}

            {!networkLost && alert && (
              <div className={`rounded-md px-3 py-2 text-[13px] ${ALERT_CLS[alert.type]}`} role="alert">
                {alert.msg}
              </div>
            )}

            <form action={formAction} noValidate className="contents">

              <div className="flex flex-col gap-1.5">
                <label htmlFor="usr" className="text-sm font-semibold text-[#212b36]">
                  Email <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    id="usr"
                    name="usr"
                    type="email"
                    autoComplete="username"
                    placeholder="you@example.com"
                    required
                    disabled={isPending}
                    aria-invalid={usrError ? "true" : undefined}
                    aria-describedby={usrError ? "usr-error" : undefined}
                    className={[
                      "w-full h-10 bg-white rounded-md pl-3.5 pr-10 text-sm text-[#212b36] placeholder-[#b8bec7] outline-none transition disabled:opacity-60",
                      "border focus:ring-2",
                      usrError
                        ? "border-red-400 focus:border-red-500 focus:ring-red-500/10"
                        : "border-[#dfe3e8] focus:border-[#6366f1] focus:ring-[#6366f1]/10",
                    ].join(" ")}
                  />
                  <span className={`absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none ${usrError ? "text-red-400" : "text-[#919eab]"}`}>
                    <Mail className="w-4 h-4" />
                  </span>
                </div>
                {usrError && (
                  <p id="usr-error" className="text-xs text-red-500 font-medium mt-0.5" role="alert">
                    {usrError}
                  </p>
                )}
              </div>

              <PasswordField isPending={isPending} error={pwdError} />

              <div className="flex items-center justify-between gap-3">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input type="checkbox" name="remember" className="w-4 h-4 rounded accent-[#6366f1] cursor-pointer" />
                  <span className="text-sm font-medium text-[#454f5b]">Remember Me</span>
                </label>
                <a href="/update-password" className="text-sm font-semibold text-[#6366f1] hover:underline whitespace-nowrap">
                  Forgot Password?
                </a>
              </div>

              {showOtp && (
                <>
                  <hr className="border-[#f0f0f0]" />
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="otp" className="text-sm font-semibold text-[#212b36]">
                      One-time code
                    </label>
                    <input
                      id="otp"
                      name="otp"
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      autoComplete="one-time-code"
                      placeholder="6-digit code"
                      maxLength={8}
                      autoFocus
                      aria-invalid={otpError ? "true" : undefined}
                      className={[
                        "w-full h-10 bg-white rounded-md px-3.5 text-sm text-[#212b36] placeholder-[#b8bec7] outline-none transition border focus:ring-2",
                        otpError
                          ? "border-red-400 focus:border-red-500 focus:ring-red-500/10"
                          : "border-[#dfe3e8] focus:border-[#6366f1] focus:ring-[#6366f1]/10",
                      ].join(" ")}
                    />
                    {otpError && (
                      <p className="text-xs text-red-500 font-medium mt-0.5" role="alert">{otpError}</p>
                    )}
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={isPending}
                className="w-full h-10 bg-[#6366f1] hover:bg-[#4f46e5] active:bg-[#4338ca] disabled:opacity-55 disabled:cursor-not-allowed text-white text-[15px] font-bold rounded-md tracking-wide transition-colors"
              >
                {isPending ? "Signing in…" : showOtp ? "Verify code" : "Sign In"}
              </button>

            </form>
          </div>

          <div className="flex justify-between items-center pt-5 border-t border-[#f4f6f8]">
            <a href="/login" className="text-xs font-semibold text-[#919eab] hover:text-[#6366f1] tracking-wide transition-colors">
              Sign in to Frappe desk →
            </a>
            <span className="text-xs text-[#919eab]">Copyrights © 2025 – Surge POS</span>
          </div>

        </div>

        <div className="flex-1 relative bg-[#1a1a2e] hidden min-[640px]:block">
          <img
            src="/assets/surge/images/pos-counter.png"
            alt="POS counter"
            className="absolute inset-0 w-full h-full object-cover object-center"
            onError={(e) => (e.currentTarget.style.display = "none")}
          />
        </div>

      </div>
    </div>
  );
}

function PasswordField({ isPending, error }: { isPending: boolean; error: string | null }) {
  const [show, setShow] = useActionState<boolean, void>((prev) => !prev, false);

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor="pwd" className="text-sm font-semibold text-[#212b36]">
        Password <span className="text-red-500">*</span>
      </label>
      <div className="relative">
        <input
          id="pwd"
          name="pwd"
          type={show ? "text" : "password"}
          autoComplete="current-password"
          placeholder="••••••••"
          required
          disabled={isPending}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? "pwd-error" : undefined}
          className={[
            "w-full h-10 bg-white rounded-md pl-3.5 pr-10 text-sm text-[#212b36] placeholder-[#b8bec7] outline-none transition disabled:opacity-60",
            "border focus:ring-2",
            error
              ? "border-red-400 focus:border-red-500 focus:ring-red-500/10"
              : "border-[#dfe3e8] focus:border-[#6366f1] focus:ring-[#6366f1]/10",
          ].join(" ")}
        />
        <button
          type="button"
          onClick={() => setShow()}
          className={`absolute right-3 top-1/2 -translate-y-1/2 transition-colors ${error ? "text-red-400 hover:text-red-500" : "text-[#919eab] hover:text-[#6366f1]"}`}
          aria-label={show ? "Hide password" : "Show password"}
          tabIndex={-1}
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {error && (
        <p id="pwd-error" className="text-xs text-red-500 font-medium mt-0.5" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
