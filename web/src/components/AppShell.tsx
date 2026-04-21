import { cn } from "@/lib/utils";

interface Props {
  children: React.ReactNode;
  className?: string;
}

/** Wraps every page — ensures min full-height and consistent font rendering. */
export function AppShell({ children, className }: Props) {
  return (
    <div className={cn("min-h-dvh w-full font-sans antialiased", className)}>
      {children}
    </div>
  );
}

/** Centered content wrapper for non-full-screen pages (profile/cashier/auth). */
export function PageContainer({ children, className }: Props) {
  return (
    <div className={cn("mx-auto w-full max-w-2xl px-4 sm:px-6", className)}>
      {children}
    </div>
  );
}
