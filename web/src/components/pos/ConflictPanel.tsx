import { useState, useEffect } from "react";
import { AlertTriangle, X, CheckCircle2, XCircle, Loader2, ShieldAlert } from "lucide-react";
import { get, post } from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface ConflictRecord {
	name: string;
	client_req_id: string;
	terminal_id: string;
	conflict_type: string;
	conflict_detail: string;
	payload: string;
	creation: string;
}

interface ParsedPayload {
	items?: { item_code: string; qty: number; rate_paise: number }[];
	payments?: { amount_paise: number }[];
}

interface Props {
	onResolved?: () => void;
}

function parsePayload(raw: string): ParsedPayload | null {
	try { return JSON.parse(raw) as ParsedPayload; }
	catch { return null; }
}

function grandTotalPaise(p: ParsedPayload | null): number {
	return (p?.payments ?? []).reduce((s, x) => s + (x.amount_paise ?? 0), 0);
}

const TYPE_COLOR: Record<string, string> = {
	"Insufficient Stock": "text-red-600 bg-red-50 border-red-200",
	"Duplicate Invoice": "text-orange-600 bg-orange-50 border-orange-200",
	"Corrupt Payload": "text-gray-600 bg-gray-50 border-gray-200",
	"Corrupt Queue Entry": "text-gray-600 bg-gray-50 border-gray-200",
};

export function ConflictPanel({ onResolved }: Props) {
	const [open, setOpen] = useState(false);
	const [conflicts, setConflicts] = useState<ConflictRecord[]>([]);
	const [active, setActive] = useState<ConflictRecord | null>(null);
	const [resolving, setResolving] = useState(false);
	const [resolveError, setResolveError] = useState("");

	async function fetchConflicts() {
		try {
			const res = await get<{ conflicts: ConflictRecord[] }>("surge.api.sync.get_conflicts");
			setConflicts(res.conflicts ?? []);
		} catch {}
	}

	useEffect(() => {
		fetchConflicts();
	}, []);

	// Realtime: push new conflict into list when panel is open
	useEffect(() => {
		const rt = window.frappe?.realtime;
		if (!rt) return;
		const onConflict = (data: unknown) => {
			const d = data as { conflict_name?: string; conflict_type?: string; detail?: string; client_request_id?: string };
			if (!d.conflict_name) return;
			const stub: ConflictRecord = {
				name: d.conflict_name,
				client_req_id: d.client_request_id ?? "",
				terminal_id: "",
				conflict_type: d.conflict_type ?? "Other",
				conflict_detail: d.detail ?? "",
				payload: "{}",
				creation: new Date().toISOString(),
			};
			setConflicts((prev) => {
				if (prev.some((c) => c.name === stub.name)) return prev;
				return [stub, ...prev];
			});
		};
		rt.on("surge:conflict_created", onConflict);
		return () => rt.off("surge:conflict_created", onConflict);
	}, []);

	async function resolve(resolution: "Approved — Force Submit" | "Rejected — Void") {
		if (!active) return;
		setResolving(true);
		setResolveError("");
		try {
			await post("surge.jobs.sync_engine.resolve_conflict", {
				conflict_name: active.name,
				resolution,
			});
			setConflicts((prev) => prev.filter((c) => c.name !== active.name));
			setActive(null);
			onResolved?.();
			if (conflicts.length <= 1) setOpen(false);
		} catch (err: unknown) {
			setResolveError((err as Error).message ?? "Failed to resolve. Try again.");
		} finally {
			setResolving(false);
		}
	}

	return (
		<div className="relative">
			<button
				type="button"
				onClick={() => { setOpen((o) => !o); if (!open) fetchConflicts(); }}
				className={cn(
					"relative flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors",
					conflicts.length > 0
						? "border-red-300 bg-red-50 text-red-600 hover:bg-red-100"
						: "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground",
				)}
				title="Sync conflicts requiring review"
			>
				<ShieldAlert className="h-3 w-3" />
				<span className="hidden sm:inline">Conflicts</span>
				{conflicts.length > 0 && (
					<span className="flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white">
						{conflicts.length}
					</span>
				)}
			</button>

			{open && (
				<>
					<div className="fixed inset-0 z-40" onClick={() => { setOpen(false); setActive(null); }} />
					<div className="absolute right-0 top-8 z-50 w-96 rounded-xl border border-[#E6EAED] bg-white shadow-2xl">
						<div className="flex items-center justify-between border-b border-[#E6EAED] px-4 py-3">
							<div className="flex items-center gap-2">
								<AlertTriangle className="h-4 w-4 text-red-500" />
								<span className="text-sm font-bold text-[#212B36]">Sync Conflicts</span>
							</div>
							<button type="button" title="Close" onClick={() => { setOpen(false); setActive(null); }}
								className="text-[#646B72] hover:text-[#212B36]">
								<X className="h-4 w-4" />
							</button>
						</div>

						{conflicts.length === 0 ? (
							<p className="px-4 py-6 text-center text-sm text-[#919EAB]">No pending conflicts</p>
						) : !active ? (
							<ul className="max-h-72 overflow-y-auto divide-y divide-[#F4F6F8]">
								{conflicts.map((c) => {
									const parsed = parsePayload(c.payload);
									const total = grandTotalPaise(parsed);
									return (
										<li key={c.name}>
											<button type="button" onClick={() => { setActive(c); setResolveError(""); }}
												className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-[#F8FAFB] transition-colors">
												<div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-50">
													<AlertTriangle className="h-4 w-4 text-red-500" />
												</div>
												<div className="min-w-0 flex-1">
													<p className={cn(
														"mb-0.5 inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold",
														TYPE_COLOR[c.conflict_type] ?? "text-gray-600 bg-gray-50 border-gray-200",
													)}>
														{c.conflict_type}
													</p>
													<p className="truncate text-xs text-[#212B36]">
														{c.terminal_id || "Unknown cashier"}
													</p>
													{total > 0 && (
														<p className="text-[11px] text-[#919EAB]">{formatCurrency(total)}</p>
													)}
												</div>
												<span className="shrink-0 text-[10px] font-medium text-red-500">Review →</span>
											</button>
										</li>
									);
								})}
							</ul>
						) : (
							<div className="p-4">
								<button type="button" onClick={() => { setActive(null); setResolveError(""); }}
									className="mb-3 flex items-center gap-1 text-xs text-[#646B72] hover:text-[#212B36]">
									← Back
								</button>

								<p className={cn(
									"mb-2 inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold",
									TYPE_COLOR[active.conflict_type] ?? "text-gray-600 bg-gray-50 border-gray-200",
								)}>
									{active.conflict_type}
								</p>
								<p className="mb-1 text-xs font-semibold text-[#212B36]">
									Cashier: {active.terminal_id || "Unknown"}
								</p>
								<p className="mb-3 rounded bg-[#F8FAFB] px-3 py-2 text-[11px] text-[#646B72]">
									{active.conflict_detail || "No detail available."}
								</p>

								{(() => {
									const parsed = parsePayload(active.payload);
									const items = parsed?.items ?? [];
									const total = grandTotalPaise(parsed);
									return items.length > 0 ? (
										<div className="mb-3 rounded border border-[#E6EAED] text-xs">
											<div className="border-b border-[#E6EAED] px-3 py-1.5 font-semibold text-[#212B36]">
												Items
											</div>
											{items.slice(0, 5).map((it, i) => (
												<div key={i} className="flex justify-between px-3 py-1.5 odd:bg-[#F8FAFB]">
													<span className="truncate text-[#212B36]">{it.item_code} × {it.qty}</span>
													<span className="shrink-0 text-[#646B72]">{formatCurrency(it.rate_paise * it.qty)}</span>
												</div>
											))}
											{items.length > 5 && (
												<p className="px-3 py-1 text-[10px] text-[#919EAB]">+{items.length - 5} more items</p>
											)}
											{total > 0 && (
												<div className="flex justify-between border-t border-[#E6EAED] px-3 py-1.5 font-semibold">
													<span>Total</span>
													<span>{formatCurrency(total)}</span>
												</div>
											)}
										</div>
									) : null;
								})()}

								{resolveError && (
									<p className="mb-3 rounded bg-red-50 px-3 py-2 text-xs text-red-600">{resolveError}</p>
								)}

								<p className="mb-2 text-[11px] text-[#919EAB]">
									<strong>Force Submit</strong> will post this invoice ignoring stock. <strong>Void</strong> will discard it permanently.
								</p>

								<div className="flex gap-2">
									<button
										type="button"
										disabled={resolving}
										onClick={() => resolve("Rejected — Void")}
										className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-red-200 py-2 text-xs font-semibold text-red-600 disabled:opacity-40 hover:bg-red-50"
									>
										{resolving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
										Void
									</button>
									<button
										type="button"
										disabled={resolving || active.conflict_type === "Corrupt Payload" || active.conflict_type === "Corrupt Queue Entry"}
										onClick={() => resolve("Approved — Force Submit")}
										className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 py-2 text-xs font-bold text-white disabled:opacity-40 hover:bg-emerald-700"
										title={active.conflict_type === "Corrupt Payload" ? "Cannot force submit — payload is corrupt" : undefined}
									>
										{resolving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
										Force Submit
									</button>
								</div>
							</div>
						)}
					</div>
				</>
			)}
		</div>
	);
}
