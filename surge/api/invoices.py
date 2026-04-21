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

	grand_total_paise = sum(p.amount_paise for p in req.payments)

	try:
		invoice_name = _submit_invoice(req)
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
	invoice.insert(ignore_permissions=True)
	invoice.submit()

	return invoice.name
