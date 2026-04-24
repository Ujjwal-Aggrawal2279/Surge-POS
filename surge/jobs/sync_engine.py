import json
import random
from datetime import datetime

import frappe
from frappe.utils import add_to_date, now_datetime

from surge.api.invoices import CreateInvoiceRequest, _submit_invoice

BATCH_SIZE = 20
MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 10
CIRCUIT_BREAKER_THRESHOLD = 10
CIRCUIT_BREAKER_COOLDOWN_MINUTES = 5
_CIRCUIT_KEY = "surge:circuit_breaker:open_until"


def _backoff_seconds(attempt: int) -> int:
	base = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
	jitter = base * 0.1 * (random.random() * 2 - 1)
	return max(1, int(base + jitter))


def _circuit_is_open() -> bool:
	open_until = frappe.cache().get_value(_CIRCUIT_KEY)
	if not open_until:
		return False
	try:
		return datetime.fromisoformat(open_until) > now_datetime()
	except (ValueError, TypeError):
		frappe.cache().delete_value(_CIRCUIT_KEY)
		return False


def _trip_circuit_breaker() -> None:
	cooldown_until = add_to_date(now_datetime(), minutes=CIRCUIT_BREAKER_COOLDOWN_MINUTES)
	frappe.cache().set_value(
		_CIRCUIT_KEY,
		cooldown_until.isoformat(),
		expires_in_sec=CIRCUIT_BREAKER_COOLDOWN_MINUTES * 60,
	)
	try:
		frappe.publish_realtime(
			"surge:circuit_breaker_tripped",
			{"cooldown_minutes": CIRCUIT_BREAKER_COOLDOWN_MINUTES},
		)
	except Exception:
		pass


def _reset_circuit_breaker() -> None:
	frappe.cache().delete_value(_CIRCUIT_KEY)


def flush_write_queue() -> None:
	if _circuit_is_open():
		return

	now = now_datetime()
	pending = frappe.get_all(
		"Surge Write Queue",
		filters={
			"status": ["in", ["Pending", "Failed"]],
			"attempt_count": ["<", MAX_ATTEMPTS],
			"next_retry_at": ["<=", now],
		},
		fields=["name", "client_req_id", "resource_type", "payload", "attempt_count"],
		order_by="creation asc",
		limit=BATCH_SIZE,
	)

	if not pending:
		return

	flushed = 0
	failed = 0
	consecutive_errors = 0

	for entry in pending:
		try:
			_mark_syncing(entry["name"])
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Surge: failed to mark {entry['name']} as Syncing: {e}")
			continue

		try:
			invoice_name = _process_entry(entry)

			_mark_done(entry["name"])
			frappe.db.commit()

			_reset_circuit_breaker()
			flushed += 1
			consecutive_errors = 0

			_safe_publish(
				"surge:invoice_submitted",
				{
					"invoice_name": invoice_name,
					"client_request_id": entry["client_req_id"],
				},
			)

		except ConflictError as e:
			try:
				_mark_conflict(entry["name"])
				frappe.db.commit()
			except Exception as db_err:
				frappe.log_error(f"Surge: failed to mark conflict for {entry['name']}: {db_err}")

			try:
				_create_conflict_record(entry, e)
				frappe.db.commit()
			except Exception as rec_err:
				frappe.log_error(f"Surge: failed to create conflict record for {entry['name']}: {rec_err}")

			failed += 1

		except Exception as e:
			attempt = (entry.get("attempt_count") or 0) + 1
			next_retry = add_to_date(now_datetime(), seconds=_backoff_seconds(attempt))
			error_msg = str(e)[:2000]

			try:
				_mark_failed(entry["name"], error_msg, next_retry, attempt)
				frappe.db.commit()
			except Exception as db_err:
				frappe.log_error(f"Surge: failed to mark {entry['name']} as Failed: {db_err}")

			frappe.log_error(f"Surge sync error on {entry['name']} (attempt {attempt}): {error_msg}")
			failed += 1
			consecutive_errors += 1

			if consecutive_errors >= CIRCUIT_BREAKER_THRESHOLD:
				_trip_circuit_breaker()
				break

	if flushed or failed:
		_safe_publish("surge:sync_complete", {"flushed": flushed, "failed": failed})


@frappe.whitelist(allow_guest=False)
def resolve_conflict(conflict_name: str, resolution: str) -> dict:
	from surge.utils.permissions import require_manager_role

	# Force-submitting or voiding a conflicted invoice is a destructive action that
	# bypasses stock validation — restrict to Manager/Administrator only.
	require_manager_role()

	valid_resolutions = {"Approved — Force Submit", "Rejected — Void"}
	if resolution not in valid_resolutions:
		frappe.throw(
			f"Invalid resolution '{resolution}'. Must be one of: {valid_resolutions}",
			frappe.ValidationError,
		)

	conflict = frappe.get_doc("Surge Sync Conflict", conflict_name)

	if conflict.resolution not in ("Pending Review",):
		frappe.throw(
			f"Conflict '{conflict_name}' is already resolved ({conflict.resolution}).",
			frappe.ValidationError,
		)

	if resolution == "Approved — Force Submit":
		import msgspec

		decoder = msgspec.json.Decoder(CreateInvoiceRequest)

		try:
			req = decoder.decode(conflict.payload.encode())
		except Exception as e:
			frappe.throw(f"Cannot decode conflict payload: {e}", frappe.ValidationError)

		original_allow_negative = frappe.db.get_single_value("Stock Settings", "allow_negative_stock")
		try:
			if not original_allow_negative:
				frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

			invoice_name = _submit_invoice(req)

			conflict.resolution = resolution
			conflict.resolved_by = frappe.session.user
			conflict.resolved_at = now_datetime()
			conflict.resulting_invoice = invoice_name
			# ignore_permissions: internal doctype; manager access enforced above.
			conflict.save(ignore_permissions=True)
			frappe.db.commit()

			return surge_response_dict({"status": "submitted", "invoice_name": invoice_name})

		finally:
			if not original_allow_negative:
				frappe.db.set_single_value("Stock Settings", "allow_negative_stock", original_allow_negative)

	conflict.resolution = resolution
	conflict.resolved_by = frappe.session.user
	conflict.resolved_at = now_datetime()
	# ignore_permissions: internal doctype; manager access enforced above.
	conflict.save(ignore_permissions=True)
	frappe.db.commit()

	return surge_response_dict({"status": "voided"})


class ConflictError(Exception):
	def __init__(self, conflict_type: str, detail: str):
		self.conflict_type = conflict_type
		self.detail = detail
		super().__init__(detail)


def _process_entry(entry: dict) -> str:
	resource_type = entry.get("resource_type")
	if resource_type == "Invoice":
		return _submit_queued_invoice(entry)
	raise ValueError(f"Unknown resource_type '{resource_type}' on entry {entry.get('name')}")


def _submit_queued_invoice(entry: dict) -> str:
	import msgspec

	decoder = msgspec.json.Decoder(CreateInvoiceRequest)

	try:
		req = decoder.decode(entry["payload"].encode())
	except Exception as e:
		raise ConflictError("Corrupt Payload", f"Cannot decode payload: {e}") from e

	_validate_stock(req, entry["client_req_id"])

	try:
		return _submit_invoice(req)
	except frappe.ValidationError as e:
		msg = str(e).lower()
		if any(kw in msg for kw in ("stock", "qty", "insufficient", "negative")):
			raise ConflictError("Insufficient Stock", str(e)) from e
		if any(kw in msg for kw in ("duplicate", "already exists", "already submitted")):
			raise ConflictError("Duplicate Invoice", str(e)) from e
		raise


def _validate_stock(req: CreateInvoiceRequest, client_req_id: str) -> None:
	allow_negative = frappe.db.get_single_value("Stock Settings", "allow_negative_stock")
	if allow_negative:
		return

	pos_profile = frappe.get_cached_doc("POS Profile", req.pos_profile)

	for item in req.items:
		warehouse = item.warehouse or pos_profile.warehouse
		available = (
			frappe.db.get_value(
				"Bin",
				{"item_code": item.item_code, "warehouse": warehouse},
				"actual_qty",
			)
			or 0.0
		)
		reserved = _get_reserved_qty(item.item_code, warehouse, exclude_req_id=client_req_id)
		net_available = float(available) - reserved

		if net_available < item.qty:
			raise ConflictError(
				"Insufficient Stock",
				(
					f"Item {item.item_code!r} in {warehouse!r}: "
					f"need {item.qty}, net available {net_available:.2f} "
					f"(actual {float(available):.2f} - reserved {reserved:.2f})"
				),
			)


def _get_reserved_qty(item_code: str, warehouse: str, exclude_req_id: str) -> float:
	rows = frappe.db.sql(
		"""
        SELECT name, payload
        FROM `tabSurge Write Queue`
        WHERE status IN ('Pending', 'Syncing')
          AND client_req_id != %s
          AND resource_type = 'Invoice'
          AND JSON_SEARCH(payload, 'one', %s, NULL, '$.items[*].item_code') IS NOT NULL
        """,
		(exclude_req_id, item_code),
		as_dict=True,
	)

	if not rows:
		return 0.0

	total = 0.0
	for row in rows:
		try:
			payload = json.loads(row["payload"])
			for item in payload.get("items", []):
				if item.get("item_code") == item_code and (item.get("warehouse") or "") == warehouse:
					total += float(item.get("qty") or 0)
		except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
			frappe.logger().warning(f"Surge: corrupt queue entry {row.get('name')} in reserved-qty calc: {e}")
			# Over-reject rather than silently under-count reserved qty
			raise ConflictError(
				"Corrupt Queue Entry",
				f"Cannot compute reserved qty — entry {row.get('name')} has invalid payload: {e}",
			) from e

	return total


def _create_conflict_record(entry: dict, error: ConflictError) -> None:
	terminal_id = frappe.db.get_value("Surge Write Queue", entry["name"], "terminal_id") or ""

	doc = frappe.new_doc("Surge Sync Conflict")
	doc.client_req_id = entry["client_req_id"]
	doc.terminal_id = terminal_id
	doc.conflict_type = error.conflict_type
	doc.conflict_detail = error.detail[:2000]
	doc.payload = entry["payload"]
	doc.resolution = "Pending Review"
	# ignore_permissions: called from flush_write_queue() background job (Administrator).
	doc.insert(ignore_permissions=True)

	_safe_publish(
		"surge:conflict_created",
		{
			"conflict_name": doc.name,
			"conflict_type": error.conflict_type,
			"detail": error.detail,
			"client_request_id": entry["client_req_id"],
		},
	)


def _mark_syncing(name: str) -> None:
	frappe.db.set_value("Surge Write Queue", name, "status", "Syncing")


def _mark_done(name: str) -> None:
	frappe.db.set_value(
		"Surge Write Queue",
		name,
		{"status": "Done", "synced_at": now_datetime()},
	)


def _mark_failed(name: str, error: str, next_retry: datetime, attempt_count: int) -> None:
	frappe.db.set_value(
		"Surge Write Queue",
		name,
		{
			"status": "Failed",
			"attempt_count": attempt_count,
			"last_error": error[:2000],
			"next_retry_at": next_retry,
		},
	)


def _mark_conflict(name: str) -> None:
	frappe.db.set_value("Surge Write Queue", name, "status", "Conflict")


def _safe_publish(event: str, data: dict) -> None:
	try:
		frappe.publish_realtime(event, data)
	except Exception as e:
		frappe.logger().warning(f"Surge: realtime publish failed for '{event}': {e}")


def surge_response_dict(data: dict) -> dict:
	return data
