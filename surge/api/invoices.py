import frappe
import msgspec
from frappe.utils import now_datetime, nowdate

from surge.jobs.queue import enqueue_invoice
from surge.utils.json import surge_response


class InvoiceItem(msgspec.Struct, gc=False):
	item_code: str
	qty: float
	rate_paise: int
	discount_paise: int = 0
	warehouse: str | None = None


class PaymentItem(msgspec.Struct, gc=False):
	mode_of_payment: str
	amount_paise: int


class CreateInvoiceRequest(msgspec.Struct, gc=False):
	client_request_id: str
	pos_profile: str
	customer: str
	items: list[InvoiceItem]
	payments: list[PaymentItem]
	offline: bool = False
	approval_token: str | None = None


_decoder = msgspec.json.Decoder(CreateInvoiceRequest)


@frappe.whitelist(allow_guest=False)
def create_invoice():
	from surge.utils.permissions import require_pos_profile_access

	raw = frappe.request.data
	try:
		req = _decoder.decode(raw)
	except Exception as e:
		frappe.throw(f"Invalid request: {e}", frappe.ValidationError)

	require_pos_profile_access(req.pos_profile)

	approval_payload = _check_discount_limits(req)

	grand_total_paise = sum(p.amount_paise for p in req.payments)

	try:
		invoice_name = _submit_invoice(req)
		if approval_payload:
			_stamp_override(invoice_name, approval_payload)
		return surge_response(
			{
				"invoice_name": invoice_name,
				"client_request_id": req.client_request_id,
				"status": "submitted",
				"grand_total_paise": grand_total_paise,
			}
		)
	except Exception:
		enqueue_invoice(req)
		return surge_response(
			{
				"invoice_name": None,
				"client_request_id": req.client_request_id,
				"status": "queued",
				"grand_total_paise": grand_total_paise,
			}
		)


def _submit_invoice(req: CreateInvoiceRequest) -> str:
	# Idempotency guard — client may retry after a network drop that happened after
	# the server already submitted. Return the existing invoice rather than creating a duplicate.
	existing = frappe.db.get_value("POS Invoice", {"surge_client_req_id": req.client_request_id}, "name")
	if existing:
		return existing

	pos_profile = frappe.get_cached_doc("POS Profile", req.pos_profile)

	invoice = frappe.new_doc("POS Invoice")
	invoice.posting_date = nowdate()
	invoice.posting_time = str(now_datetime().time())
	invoice.pos_profile = req.pos_profile
	invoice.customer = req.customer
	invoice.company = pos_profile.company
	invoice.currency = pos_profile.currency
	invoice.selling_price_list = pos_profile.selling_price_list
	invoice.set_warehouse = pos_profile.warehouse
	invoice.surge_client_req_id = req.client_request_id

	for item in req.items:
		invoice.append(
			"items",
			{
				"item_code": item.item_code,
				"qty": item.qty,
				"rate": item.rate_paise / 100.0,
				"discount_amount": item.discount_paise / 100.0,
				"warehouse": item.warehouse or pos_profile.warehouse,
			},
		)

	for payment in req.payments:
		invoice.append(
			"payments",
			{
				"mode_of_payment": payment.mode_of_payment,
				"amount": payment.amount_paise / 100.0,
			},
		)

	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()
	# ignore_permissions: access already enforced upstream via require_pos_profile_access().
	# POS users intentionally lack direct DocType-level Create on POS Invoice — they
	# transact only through Surge POS, not ERPNext Desk.
	invoice.insert(ignore_permissions=True)
	invoice.submit()

	return invoice.name


def _check_discount_limits(req: CreateInvoiceRequest) -> dict | None:
	"""
	Returns the approval payload if a valid token was consumed, None if no discount
	exceeded the limit. Raises ValidationError if discount exceeds limit with no valid token.
	"""
	from surge.api.auth import verify_approval_token

	if not req.items:
		return None

	profile_doc = frappe.get_cached_doc("POS Profile", req.pos_profile)

	# Respect ERPNext's native master switch before applying Surge role-based limits
	any_discount = any(i.discount_paise > 0 for i in req.items)
	if any_discount and not profile_doc.allow_discount_change:
		frappe.throw("Discounts are disabled on this POS Profile.", frappe.ValidationError)

	cashier = frappe.session.user
	access_level = (
		frappe.db.get_value(
			"POS Profile User",
			{"parent": req.pos_profile, "user": cashier, "status": "Active"},
			"access_level",
		)
		or "Cashier"
	)

	limit_map = {
		"Cashier": float(getattr(profile_doc, "discount_limit_cashier", 5) or 5),
		"Supervisor": float(getattr(profile_doc, "discount_limit_supervisor", 15) or 15),
		"Manager": float(getattr(profile_doc, "discount_limit_manager", 100) or 100),
	}
	max_pct = limit_map.get(access_level, 5)

	max_item_pct = 0.0
	for item in req.items:
		if item.rate_paise > 0 and item.discount_paise > 0:
			pct = (item.discount_paise / item.rate_paise) * 100
			max_item_pct = max(max_item_pct, pct)

	if max_item_pct <= max_pct:
		return None

	# Discount exceeds limit — validate approval token
	if req.approval_token:
		payload = verify_approval_token(req.approval_token)
		if payload and payload.get("action") == "discount_override":
			return payload

	frappe.throw(
		f"Discount of {max_item_pct:.1f}% exceeds your {access_level} "
		f"limit of {max_pct:.0f}%. A Supervisor or Manager must approve.",
		frappe.ValidationError,
		title="Approval Required",
	)


def _stamp_override(invoice_name: str, payload: dict) -> None:
	frappe.db.set_value(
		"POS Invoice",
		invoice_name,
		{
			"override_approved_by": payload.get("approver"),
			"override_approved_at": payload.get("ts"),
			"override_reason": f"discount_override approved by {payload.get('approver')} ({payload.get('access_level')})",
		},
	)
