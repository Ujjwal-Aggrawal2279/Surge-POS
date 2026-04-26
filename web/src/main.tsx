import React, { lazy, Suspense, useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AppShell } from "@/components/AppShell";
import { LoginScreen } from "@/pages/LoginScreen";
import { HomeSelector } from "@/pages/HomeSelector";
import { Loader2 } from "lucide-react";
import { saveSession, loadSession, clearSession } from "@/lib/session";
import { initRealtime, subscribeToSurgeEvents } from "@/lib/realtime";
import { get } from "@/lib/api";
import type { Cashier, POSProfile, Session } from "@/types/pos";
import "./index.css";

// Eagerly loaded above — shown immediately for guests, no Suspense flash.
// Authenticated pages lazy-load only when the user reaches them.
const ProfileSelector  = lazy(() => import("@/pages/ProfileSelector").then(m => ({ default: m.ProfileSelector })));
const CashierScreen    = lazy(() => import("@/pages/CashierScreen").then(m => ({ default: m.CashierScreen })));
const SellScreen       = lazy(() => import("@/pages/SellScreen").then(m => ({ default: m.SellScreen })));
const ShiftOpen        = lazy(() => import("@/pages/ShiftOpen").then(m => ({ default: m.ShiftOpen })));
const DashboardScreen  = lazy(() => import("@/pages/DashboardScreen").then(m => ({ default: m.DashboardScreen })));

type AppMode = "checking" | "home-selector" | "dashboard" | "pos";

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
    <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/70 backdrop-blur-sm">
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
  const [posSession, setPosSession] = useState<Session | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // If the URL already points to a dashboard page (path or legacy hash), skip HomeSelector
  const isDashboardUrl =
    window.location.pathname.startsWith("/surge/dashboard") ||
    window.location.hash.startsWith("#/dashboard");
  const [appMode, setAppMode] = useState<AppMode>(isDashboardUrl ? "dashboard" : "checking");

  // Must be before any early return — rules of hooks
  useEffect(() => {
    const handle = () => setSessionExpired(true);
    window.addEventListener("surge:session-expired", handle);
    return () => window.removeEventListener("surge:session-expired", handle);
  }, []);

  // Check manager access once on mount (skip if hash already determined mode)
  useEffect(() => {
    if (isGuest || isDashboardUrl) return;
    get<{ is_manager: boolean }>("surge.api.dashboard.is_manager")
      .then((res) => setAppMode(res.is_manager ? "home-selector" : "pos"))
      .catch(() => setAppMode("pos")); // degraded: treat as cashier
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleLogin(p: POSProfile, c: Cashier) {
    saveSession(p, c);
    setProfile(p);
    setCashier(c);
    setPosSession(null); // force ShiftOpen gate on new login
  }

  function handleLock() {
    clearSession();
    setCashier(null);
    setPosSession(null);
  }

  function handleChangeProfile() {
    clearSession();
    setProfile(null);
    setCashier(null);
    setPosSession(null);
  }

  if (isGuest) return <LoginScreen />;

  if (appMode === "checking") {
    return <div className="flex h-dvh items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#6938EF]" /></div>;
  }

  if (appMode === "dashboard") {
    return (
      <DashboardScreen
        onGoToPOS={() => {
          window.location.hash = "";
          setAppMode("pos");
        }}
      />
    );
  }

  if (appMode === "home-selector") {
    return (
      <HomeSelector
        userFullName={window.SURGE_CONFIG?.user_fullname ?? ""}
        onSelectDashboard={() => {
          window.location.hash = "#/dashboard";
          setAppMode("dashboard");
        }}
        onSelectPOS={() => setAppMode("pos")}
      />
    );
  }

  // appMode === "pos" — existing POS flow
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

  // ShiftOpen gate — check for active POS Opening Entry before selling
  if (!posSession) {
    return (
      <ShiftOpenGate
        profile={profile}
        onSessionReady={setPosSession}
      />
    );
  }

  return (
    <>
      {sessionExpired && <SessionExpiredOverlay onDismiss={() => setSessionExpired(false)} />}
      <SellScreen
        profile={profile}
        cashier={cashier}
        posSession={posSession}
        onLock={handleLock}
        onChangeProfile={handleChangeProfile}
        onShiftClosed={() => setPosSession(null)}
      />
    </>
  );
}

// Separate component so ShiftOpen can call useSession internally without
// violating hooks ordering in App (posSession may be null or truthy)
function ShiftOpenGate({ profile, onSessionReady }: { profile: POSProfile; onSessionReady: (s: Session) => void }) {
  return (
    <ShiftOpen
      profile={profile}
      onSessionOpen={onSessionReady}
    />
  );
}

// Initialize Socket.IO immediately — sets window.frappe.realtime synchronously
// so all components can subscribe without retry loops
if (window.SURGE_CONFIG?.user && window.SURGE_CONFIG.user !== "Guest") {
  initRealtime();
  subscribeToSurgeEvents(queryClient);
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
