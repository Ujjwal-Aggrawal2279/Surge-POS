import { useState, useEffect, useCallback } from "react";
import { get, post } from "@/lib/api";
import type { Session, SessionBalance, ZReport } from "@/types/pos";

interface SessionState {
  session: Session | null;
  stale: boolean;
  loading: boolean;
  error: string | null;
}

export function useSession(posProfile: string) {
  const [state, setState] = useState<SessionState>({
    session: null,
    stale: false,
    loading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await get<{ session: Session | null; stale?: boolean }>(
        "surge.api.session.get_active_session",
        { pos_profile: posProfile },
      );
      setState({ session: data.session, stale: !!data.stale, loading: false, error: null });
    } catch (e) {
      setState((s) => ({ ...s, loading: false, error: (e as Error).message }));
    }
  }, [posProfile]);

  useEffect(() => { refresh(); }, [refresh]);

  async function openSession(balances: SessionBalance[]): Promise<{ session_name: string; period_start_date: string }> {
    const data = await post<{ session_name: string; period_start_date: string }>(
      "surge.api.session.open_session",
      { pos_profile: posProfile, opening_balances: balances },
    );
    await refresh();
    return data;
  }

  async function closeSession(
    openingEntry: string,
    closingBalances: SessionBalance[],
    discrepancyReason?: string,
  ): Promise<ZReport> {
    const data = await post<{ z_report: ZReport }>(
      "surge.api.session.close_session",
      {
        opening_entry: openingEntry,
        closing_balances: closingBalances,
        discrepancy_reason: discrepancyReason ?? "",
      },
    );
    refresh().catch(() => {}); // update local state; don't block or propagate failures
    return data.z_report;
  }

  return { ...state, refresh, openSession, closeSession };
}
