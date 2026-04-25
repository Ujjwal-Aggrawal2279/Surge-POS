import frappe

TEST_HSN = "9999"


def ensure_master_data():
	"""Create minimum required master records for a fresh ERPNext site (no setup wizard)."""
	if not frappe.db.exists("UOM", "Nos"):
		uom = frappe.new_doc("UOM")
		uom.uom_name = "Nos"
		uom.insert(ignore_permissions=True)

	for name, mop_type in [("Cash", "Cash"), ("UPI", "General")]:
		if not frappe.db.exists("Mode of Payment", name):
			mop = frappe.new_doc("Mode of Payment")
			mop.mode_of_payment = name
			mop.type = mop_type
			mop.insert(ignore_permissions=True)

	# india_compliance enforces HSN on every Item — create a generic test code
	if not frappe.db.exists("GST HSN Code", TEST_HSN):
		hsn = frappe.new_doc("GST HSN Code")
		hsn.hsn_code = TEST_HSN
		hsn.description = "General Goods (Test)"
		hsn.insert(ignore_permissions=True)

	frappe.db.commit()
