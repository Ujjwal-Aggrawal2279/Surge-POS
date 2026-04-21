import { useEffect } from "react";
import { Loader2, Store } from "lucide-react";
import { useProfiles } from "@/hooks/useItems";
import { config } from "@/lib/api";
import type { POSProfile } from "@/types/pos";

interface Props {
  onSelect: (profile: POSProfile) => void;
}

export function ProfileSelector({ onSelect }: Props) {
  const cfg = config();
  const { data, isLoading, error } = useProfiles();

  const profiles = data?.profiles ?? [];

  // Auto-select when only one profile is accessible — no point showing a list of one
  useEffect(() => {
    if (!isLoading && profiles.length === 1) {
      onSelect(profiles[0]!);
    }
  }, [isLoading, profiles.length]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading || profiles.length === 1) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center text-destructive">
        <p>Failed to load profiles: {(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col items-center justify-center bg-muted/30 p-6">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-primary">Surge POS</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Welcome, {cfg.user_fullname || cfg.user}. Select a POS profile to continue.
        </p>
      </div>

      {profiles.length === 0 ? (
        <div className="rounded-lg border bg-background p-8 text-center text-sm text-muted-foreground">
          No POS profiles are assigned to you.
          <br />
          Ask your manager to add you to a POS Profile.
        </div>
      ) : (
        <div className="grid w-full max-w-lg gap-3">
          {profiles.map((profile) => (
            <button
              key={profile.name}
              type="button"
              onClick={() => onSelect(profile)}
              className="flex items-center gap-4 rounded-lg border bg-background px-5 py-4 text-left transition-colors hover:border-primary hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              <Store className="h-5 w-5 shrink-0 text-primary" />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{profile.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {profile.warehouse} · {profile.currency}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
