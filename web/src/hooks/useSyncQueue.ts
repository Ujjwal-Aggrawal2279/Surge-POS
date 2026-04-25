import { useState, useEffect, useCallback, useRef } from "react";
import { post } from "@/lib/api";
import { dequeue, getAllPending, pendingCount as getCount } from "@/lib/offline-queue";

interface InvoiceResult {
	status: "submitted" | "queued";
	invoice_name: string | null;
}

export function useSyncQueue() {
	const [pendingCount, setPendingCount] = useState(0);
	const [isSyncing, setIsSyncing] = useState(false);
	const [circuitOpen, setCircuitOpen] = useState(false);
	const draining = useRef(false);

	const refreshCount = useCallback(async () => {
		try {
			const n = await getCount();
			setPendingCount(n);
		} catch {}
	}, []);

	const drain = useCallback(async () => {
		if (draining.current || !navigator.onLine) return;
		const pending = await getAllPending().catch(() => [] as Awaited<ReturnType<typeof getAllPending>>);
		if (!pending.length) return;

		draining.current = true;
		setIsSyncing(true);

		for (const req of pending) {
			if (!navigator.onLine) break;
			try {
				const result = await post<InvoiceResult>("surge.api.invoices.create_invoice", req);
				if (result.status === "submitted") {
					await dequeue(req.client_request_id).catch(() => {});
				}
			} catch {
				// Network error — leave in queue, retry on next reconnect
			}
		}

		draining.current = false;
		setIsSyncing(false);
		await refreshCount();
	}, [refreshCount]);

	// Poll IndexedDB count every 5s (no native change events)
	useEffect(() => {
		refreshCount();
		const id = setInterval(refreshCount, 5_000);
		return () => clearInterval(id);
	}, [refreshCount]);

	// Drain on reconnect + on mount if already online
	useEffect(() => {
		if (navigator.onLine) drain();
		const onOnline = () => {
			setCircuitOpen(false);
			drain();
		};
		window.addEventListener("online", onOnline);
		return () => window.removeEventListener("online", onOnline);
	}, [drain]);

	// Realtime: server confirmed a queued invoice synced — dequeue from IndexedDB
	useEffect(() => {
		const rt = window.frappe?.realtime;
		if (!rt) return;

		const onSubmitted = (data: unknown) => {
			const d = data as { client_request_id?: string };
			if (d.client_request_id) dequeue(d.client_request_id).catch(() => {});
			refreshCount();
		};
		const onCircuit = () => setCircuitOpen(true);

		rt.on("surge:invoice_submitted", onSubmitted);
		rt.on("surge:circuit_breaker_tripped", onCircuit);

		return () => {
			rt.off("surge:invoice_submitted", onSubmitted);
			rt.off("surge:circuit_breaker_tripped", onCircuit);
		};
	}, [refreshCount]);

	return { pendingCount, isSyncing, circuitOpen, setCircuitOpen };
}
