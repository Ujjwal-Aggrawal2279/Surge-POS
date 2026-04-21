import { useState, useCallback, useEffect } from "react";
import { Delete } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  maxLength?: number;
  minLength?: number;
  onSubmit: (pin: string) => Promise<void> | void;
  disabled?: boolean;
  /** Increment to trigger shake + clear */
  errorCount?: number;
  message?: string;
  messageType?: "error" | "warning" | "info";
}

export function PinPad({
  maxLength = 6,
  minLength = 4,
  onSubmit,
  disabled = false,
  errorCount = 0,
  message,
  messageType = "error",
}: Props) {
  const [pin, setPin] = useState("");
  const [shaking, setShaking] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (errorCount === 0) return;
    setPin("");
    setShaking(true);
    const t = setTimeout(() => setShaking(false), 500);
    return () => clearTimeout(t);
  }, [errorCount]);

  const submit = useCallback(
    async (value: string) => {
      if (value.length < minLength) return;
      setSubmitting(true);
      try {
        await onSubmit(value);
      } finally {
        setSubmitting(false);
        setPin("");
      }
    },
    [onSubmit, minLength],
  );

  const append = useCallback(
    (digit: string) => {
      if (disabled || submitting) return;
      setPin((prev) => {
        const next = prev + digit;
        if (next.length > maxLength) return prev;
        if (next.length >= maxLength) void submit(next);
        return next;
      });
    },
    [disabled, submitting, maxLength, submit],
  );

  const backspace = useCallback(() => {
    if (disabled || submitting) return;
    setPin((prev) => prev.slice(0, -1));
  }, [disabled, submitting]);

  // Hardware numpad / keyboard support
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (disabled || submitting) return;
      if (e.key >= "0" && e.key <= "9") { e.preventDefault(); append(e.key); }
      else if (e.key === "Backspace") { e.preventDefault(); backspace(); }
      else if (e.key === "Enter") { e.preventDefault(); void submit(pin); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [append, backspace, submit, pin, disabled, submitting]);

  const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

  return (
    <div className="flex flex-col items-center gap-4 select-none w-full" aria-label="PIN entry pad">

      {/* ── Digit boxes ── */}
      <div
        className={cn("flex gap-2.5", shaking && "animate-[shake_.45s_ease-in-out]")}
        role="status"
        aria-live="polite"
        aria-label={`${pin.length} of ${maxLength} digits entered`}
      >
        {Array.from({ length: maxLength }, (_, i) => {
          const filled = i < pin.length;
          return (
            <div
              key={i}
              className={cn(
                "w-11 h-14 rounded-lg border-2 flex items-center justify-center transition-all duration-150",
                filled && !shaking  && "border-[#6366f1]",
                filled && shaking   && "border-red-400",
                !filled             && "border-[#dfe3e8]",
              )}
            >
              {filled && (
                <div className={cn(
                  "w-2.5 h-2.5 rounded-full",
                  shaking ? "bg-red-400" : "bg-[#6366f1]",
                )} />
              )}
            </div>
          );
        })}
      </div>

      {/* ── Message ── */}
      <div className="h-5 text-[13px] text-center font-medium">
        {message && (
          <span className={cn(
            messageType === "error"   && "text-red-500",
            messageType === "warning" && "text-amber-500",
            messageType === "info"    && "text-blue-600",
          )}>
            {message}
          </span>
        )}
      </div>

      {/* ── Numpad ── */}
      <div className="grid grid-cols-3 gap-2.5" role="group" aria-label="PIN keypad">
        {KEYS.map((key, i) => {
          if (key === "") return <div key={i} />;
          const isBack = key === "⌫";
          return (
            <button
              key={i}
              type="button"
              onClick={() => (isBack ? backspace() : append(key))}
              disabled={disabled || submitting || (!isBack && pin.length >= maxLength)}
              className={cn(
                "flex items-center justify-center rounded-xl",
                "h-14 w-14 text-xl font-semibold",
                "bg-white border border-[#f0f0f0] shadow-sm",
                "hover:border-[#6366f1]/30 hover:bg-[#f5f5ff] active:scale-95 transition-all",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                isBack ? "text-[#919eab]" : "text-[#212b36]",
              )}
              aria-label={isBack ? "Backspace" : key}
            >
              {isBack ? <Delete className="h-5 w-5" /> : key}
            </button>
          );
        })}
      </div>

      {/* ── Verify button for variable-length PINs ── */}
      {pin.length >= minLength && pin.length < maxLength && (
        <button
          type="button"
          onClick={() => void submit(pin)}
          disabled={submitting}
          className="w-full h-10 bg-[#6366f1] hover:bg-[#4f46e5] active:bg-[#4338ca] disabled:opacity-55 text-white text-[15px] font-bold rounded-md transition-colors"
        >
          {submitting ? "Verifying…" : "Verify"}
        </button>
      )}
    </div>
  );
}
