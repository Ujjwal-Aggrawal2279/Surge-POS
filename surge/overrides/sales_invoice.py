import frappe


def on_submit(doc, method=None):
	if not doc.is_pos:
		return

	_write_audit(
		action_type="invoice_submit",
		user=doc.owner,
		pos_profile=doc.pos_profile or "",
		invoice=doc.name,
		new_value=str(doc.grand_total),
	)

	try:
		frappe.publish_realtime(
			"surge:invoice_submitted",
			{
				"invoice_name": doc.name,
				"client_request_id": doc.get("surge_client_req_id") or "",
			},
		)
	except Exception:
		pass


def before_cancel(doc, method=None):
	if not doc.is_pos:
		return
	if not doc.get("void_reason"):
		frappe.throw(
			"A void reason is required before cancelling this invoice.",
			frappe.ValidationError,
			title="Void Reason Required",
		)
	_write_audit(
		action_type="void_transaction",
		user=frappe.session.user,
		pos_profile=doc.pos_profile or "",
		invoice=doc.name,
		old_value=f"grand_total={doc.grand_total}",
		new_value=f"void_reason={doc.void_reason}",
	)


def _write_audit(
	action_type: str, user: str, pos_profile: str, invoice: str, old_value: str = "", new_value: str = ""
) -> None:
	try:
		if not frappe.db.table_exists("POS Security Audit Log"):
			return
		doc = frappe.new_doc("POS Security Audit Log")
		doc.action_type = action_type
		doc.user = user
		doc.pos_profile = pos_profile
		doc.invoice = invoice
		doc.old_value = old_value[:140]
		doc.new_value = new_value[:140]
		doc.terminal_id = frappe.session.user
		try:
			doc.ip_address = frappe.request.remote_addr if frappe.request else ""
		except Exception:
			doc.ip_address = ""
		doc.insert(ignore_permissions=True, ignore_links=True)
	except Exception as e:
		frappe.logger().warning(f"Surge: audit log write failed in sales_invoice hook: {e}")
