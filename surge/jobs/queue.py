import frappe
from frappe.utils import now_datetime


def enqueue_invoice(req) -> None:
    import msgspec

    payload = msgspec.json.encode(req).decode()

    doc = frappe.new_doc("Surge Write Queue")
    doc.client_req_id = req.client_request_id
    doc.terminal_id = frappe.session.user
    doc.resource_type = "Invoice"
    doc.payload = payload
    doc.status = "Pending"
    doc.attempt_count = 0
    doc.next_retry_at = now_datetime()

    try:
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except frappe.DuplicateEntryError:
        frappe.db.rollback()
    except Exception:
        frappe.db.rollback()
        raise
