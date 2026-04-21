import React, { lazy, Suspense, useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AppShell } from "@/components/AppShell";
import { LoginScreen } from "@/pages/LoginScreen";
import { Loader2 } from "lucide-react";
import { saveSession, loadSession, clearSession } from "@/lib/session";
import type { Cashier, POSProfile } from "@/types/pos";
import "./index.css";

// Eagerly loaded above — shown immediately for guests, no Suspense flash.
// Authenticated pages lazy-load only when the user reaches them.
const ProfileSelector = lazy(() => import("@/pages/ProfileSelector").then(m => ({ default: m.ProfileSelector })));
const CashierScreen   = lazy(() => import("@/pages/CashierScreen").then(m => ({ default: m.CashierScreen })));
const SellScreen      = lazy(() => import("@/pages/SellScreen").then(m => ({ default: m.SellScreen })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => {
        if ((error as { status?: number }).status === 401) return false;
        if ((error as { status?: number }).status === 403) return false;
        return count < 3;
      },
      networkMode: "always",
    },
    mutations: {
      networkMode: "always",
    },
  },
});

function PageSpinner() {
  return (
    <div className="flex h-dvh items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

function SessionExpiredOverlay({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="mx-4 max-w-sm rounded-2xl border border-border bg-card p-6 text-center shadow-xl">
        <h2 className="mb-2 text-lg font-semibold">Session expired</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Your session has timed out. Sign in again — your cart is saved.
        </p>
        <a
          href="/surge"
          className="inline-block rounded-lg bg-primary px-6 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          onClick={onDismiss}
        >
          Sign in again
        </a>
      </div>
    </div>
  );
}

function App() {
  const isGuest = window.SURGE_CONFIG?.user === "Guest" || !window.SURGE_CONFIG?.user;

  // Restore persisted cashier session (survives F5, cleared on tab close or Lock)
  const persisted = !isGuest ? loadSession() : null;

  const [profile, setProfile] = useState<POSProfile | null>(persisted?.profile ?? null);
  const [cashier, setCashier] = useState<Cashier | null>(persisted?.cashier ?? null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Must be before any early return — rules of hooks
  useEffect(() => {
    const handle = () => setSessionExpired(true);
    window.addEventListener("surge:session-expired", handle);
    return () => window.removeEventListener("surge:session-expired", handle);
  }, []);

  function handleLogin(p: POSProfile, c: Cashier) {
    saveSession(p, c);
    setProfile(p);
    setCashier(c);
  }

  function handleLock() {
    clearSession();
    setCashier(null);
  }

  function handleChangeProfile() {
    clearSession();
    setProfile(null);
    setCashier(null);
  }

  if (isGuest) return <LoginScreen />;

  if (!profile) {
    return <ProfileSelector onSelect={setProfile} />;
  }

  if (!cashier) {
    return (
      <CashierScreen
        profile={profile}
        onLogin={(c) => handleLogin(profile, c)}
        onChangeProfile={handleChangeProfile}
      />
    );
  }

  return (
    <>
      {sessionExpired && <SessionExpiredOverlay onDismiss={() => setSessionExpired(false)} />}
      <SellScreen
        profile={profile}
        cashier={cashier}
        onLock={handleLock}
        onChangeProfile={handleChangeProfile}
      />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppShell>
          <Suspense fallback={<PageSpinner />}>
            <App />
          </Suspense>
        </AppShell>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
