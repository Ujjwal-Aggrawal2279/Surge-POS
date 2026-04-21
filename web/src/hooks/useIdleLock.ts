import { useEffect, useRef, useState, useCallback } from "react";

const EVENTS: (keyof WindowEventMap)[] = [
  "mousemove", "mousedown", "keydown", "touchstart", "touchmove", "scroll", "wheel",
];

interface IdleLock {
  isWarning: boolean;
  secondsLeft: number;
  dismissWarning: () => void;
}

export function useIdleLock(
  timeoutMs: number,
  onLock: () => void,
  options: { warnBeforeMs?: number; disabled?: boolean } = {},
): IdleLock {
  const { warnBeforeMs = 60_000, disabled = false } = options;

  const [secondsLeft, setSecondsLeft] = useState(0);
  const [isWarning, setIsWarning] = useState(false);

  const lastActivityRef = useRef(Date.now());
  const lockTimerRef    = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warnTimerRef    = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const onLockRef       = useRef(onLock);
  onLockRef.current = onLock;

  const clearAllTimers = useCallback(() => {
    if (lockTimerRef.current)    clearTimeout(lockTimerRef.current);
    if (warnTimerRef.current)    clearTimeout(warnTimerRef.current);
    if (countdownRef.current)    clearInterval(countdownRef.current);
    lockTimerRef.current = warnTimerRef.current = countdownRef.current = null;
  }, []);

  const startCountdown = useCallback(() => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    setSecondsLeft(Math.round(warnBeforeMs / 1000));
    countdownRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          if (countdownRef.current) clearInterval(countdownRef.current);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  }, [warnBeforeMs]);

  const schedule = useCallback(() => {
    clearAllTimers();
    setIsWarning(false);

    warnTimerRef.current = setTimeout(() => {
      setIsWarning(true);
      startCountdown();
      lockTimerRef.current = setTimeout(() => {
        clearAllTimers();
        setIsWarning(false);
        onLockRef.current();
      }, warnBeforeMs);
    }, timeoutMs - warnBeforeMs);
  }, [timeoutMs, warnBeforeMs, clearAllTimers, startCountdown]);

  const resetTimer = useCallback(() => {
    lastActivityRef.current = Date.now();
    schedule();
  }, [schedule]);

  const dismissWarning = useCallback(() => {
    resetTimer();
    setIsWarning(false);
  }, [resetTimer]);

  useEffect(() => {
    if (disabled) {
      clearAllTimers();
      setIsWarning(false);
      return;
    }

    schedule();

    EVENTS.forEach((e) => window.addEventListener(e, resetTimer, { passive: true }));
    const onVisible = () => { if (!document.hidden) resetTimer(); };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearAllTimers();
      EVENTS.forEach((e) => window.removeEventListener(e, resetTimer));
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [disabled, schedule, resetTimer, clearAllTimers]);

  return { isWarning, secondsLeft, dismissWarning };
}
