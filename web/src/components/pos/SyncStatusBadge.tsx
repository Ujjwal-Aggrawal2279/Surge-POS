import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
	isOnline: boolean;
	pendingCount: number;
	isSyncing: boolean;
}

export function SyncStatusBadge({ isOnline, pendingCount, isSyncing }: Props) {
	const hasPending = pendingCount > 0;

	let label: string;
	let colorClass: string;
	let dotClass: string;

	if (isOnline && !hasPending) {
		label = "Online";
		colorClass = "bg-emerald-50 text-emerald-600";
		dotClass = "bg-emerald-500";
	} else if (isOnline && isSyncing) {
		label = `Syncing ${pendingCount}…`;
		colorClass = "bg-amber-50 text-amber-600";
		dotClass = "bg-amber-500";
	} else if (isOnline && hasPending) {
		label = `${pendingCount} queued`;
		colorClass = "bg-amber-50 text-amber-600";
		dotClass = "bg-amber-500 animate-pulse";
	} else if (!isOnline && hasPending) {
		label = `Offline · ${pendingCount} queued`;
		colorClass = "bg-amber-50 text-amber-600";
		dotClass = "bg-amber-500 animate-pulse";
	} else {
		label = "Offline";
		colorClass = "bg-amber-50 text-amber-600";
		dotClass = "bg-amber-500 animate-pulse";
	}

	return (
		<span className={cn("flex items-center gap-1.5 rounded-full px-2 py-0.5 font-medium", colorClass)}>
			{isSyncing && isOnline ? (
				<Loader2 className="h-3 w-3 animate-spin" />
			) : (
				<span className={cn("h-1.5 w-1.5 rounded-full", dotClass)} />
			)}
			{label}
		</span>
	);
}
