import frappe
import msgspec
from frappe.utils import now_datetime

from surge.api.auth import verify_approval_token
from surge.jobs.queue import enqueue_invoice
from surge.utils.json import surge_response
from surge.utils.permissions import require_pos_profile_access, require_warehouse_access


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
	except (frappe.ValidationError, frappe.PermissionError, frappe.AuthenticationError):
		# Business-rule failures must surface as errors — never silently enqueue
		raise
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
	# Idempotency guard — scoped to the submitting user so Cashier B cannot claim
	# Cashier A's invoice by reusing the same client_request_id.
	existing = frappe.db.get_value(
		"Sales Invoice",
		{"surge_client_req_id": req.client_request_id, "owner": frappe.session.user},
		"name",
	)
	if existing:
		return existing

	pos_profile = frappe.get_cached_doc("POS Profile", req.pos_profile)

	# Validate payment modes against profile — prevent ghost/invalid modes
	allowed_modes = {p.mode_of_payment for p in pos_profile.payments}
	for payment in req.payments:
		if payment.mode_of_payment not in allowed_modes:
			frappe.throw(
				f"Payment mode '{payment.mode_of_payment}' is not configured on this POS Profile.",
				frappe.ValidationError,
			)

	# Capture timestamp once — prevents posting_date and posting_time straddling midnight
	now = now_datetime()

	invoice = frappe.new_doc("Sales Invoice")
	invoice.is_pos = 1
	invoice.update_stock = 1
	invoice.posting_date = now.date()
	invoice.posting_time = str(now.time())
	invoice.pos_profile = req.pos_profile
	invoice.customer = req.customer
	invoice.company = pos_profile.company
	invoice.currency = pos_profile.currency
	invoice.selling_price_list = pos_profile.selling_price_list
	invoice.surge_client_req_id = req.client_request_id

	for item in req.items:
		if item.qty <= 0:
			frappe.throw(f"Item '{item.item_code}': qty must be greater than zero.", frappe.ValidationError)
		if item.rate_paise < 0:
			frappe.throw(f"Item '{item.item_code}': rate cannot be negative.", frappe.ValidationError)
		if item.discount_paise < 0:
			frappe.throw(f"Item '{item.item_code}': discount cannot be negative.", frappe.ValidationError)
		if item.discount_paise > item.rate_paise:
			frappe.throw(f"Item '{item.item_code}': discount exceeds rate.", frappe.ValidationError)
		# Validate warehouse is accessible to this user — prevents cross-terminal stock manipulation
		effective_warehouse = item.warehouse or pos_profile.warehouse
		require_warehouse_access(effective_warehouse)
		invoice.append(
			"items",
			{
				"item_code": item.item_code,
				"qty": item.qty,
				"rate": item.rate_paise / 100.0,
				"discount_amount": item.discount_paise / 100.0,
				"warehouse": effective_warehouse,
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

	# POS users lack broad DocType permissions by design — they transact only through
	# Surge POS. ignore_permissions covers set_missing_values() (which checks Customer
	# read) and insert/submit. Access is enforced upstream by require_pos_profile_access().
	prev = frappe.flags.ignore_permissions
	frappe.flags.ignore_permissions = True
	try:
		invoice.set_missing_values()
		invoice.calculate_taxes_and_totals()
		invoice.insert(ignore_permissions=True)
		invoice.submit()
	finally:
		frappe.flags.ignore_permissions = prev

	return invoice.name


def _check_discount_limits(req: CreateInvoiceRequest) -> dict | None:
	"""
	Returns the approval payload if a valid token was consumed, None if no discount
	exceeded the limit. Raises ValidationError if discount exceeds limit with no valid token.
	"""
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
		"Sales Invoice",
		invoice_name,
		{
			"override_approved_by": payload.get("approver"),
			"override_approved_at": payload.get("ts"),
			"override_reason": f"discount_override approved by {payload.get('approver')} ({payload.get('access_level')})",
		},
	)
