import { Component, type ErrorInfo, type ReactNode } from "react";
import { RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  /**
   * Optional custom fallback. Receives the caught error.
   * Defaults to a full-screen recovery prompt.
   */
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches any unhandled React render error and shows a recovery UI
 * instead of a blank screen.
 *
 * Wrap at every major UI boundary (whole app, sell screen, payment dialog)
 * so a crash in one area doesn't kill the entire POS session.
 *
 * Worst case: a component crashes mid-render. Without this, the cashier
 * sees a white screen with no recovery path. With this, they get a clear
 * message and a one-click reload.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log to Frappe error log in production
    console.error("[Surge POS] Unhandled render error:", error, info.componentStack);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) {
      return this.props.fallback(error, this.reset);
    }

    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background p-8 text-center">
        <div className="rounded-full bg-destructive/10 p-4">
          <RefreshCw className="h-8 w-8 text-destructive" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-destructive">Something went wrong</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {error.message || "An unexpected error occurred."}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={this.reset}
            className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            Try again
          </button>
          <button
            type="button"
            onClick={() => location.reload()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Reload POS
          </button>
        </div>
      </div>
    );
  }
}
