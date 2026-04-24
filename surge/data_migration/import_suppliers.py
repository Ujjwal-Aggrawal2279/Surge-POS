"""
Supplier Master Import — 3 Suppliers

Run:
  bench --site <site> console
  >>> from surge.data_migration.import_suppliers import run; run()

Creates per supplier:
  - Supplier (with GSTIN, PAN, group)
  - Address  (Billing, linked via Dynamic Link)
  - Contact  (linked via Dynamic Link)
"""

import frappe

XLSX_PATH = "/home/ubuntu22/Downloads/3 Supplier Master.xlsx"
SUPPLIER_GROUP = "Wholesale"
COUNTRY = "India"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
	_log("Starting supplier master import")

	_setup_prerequisites()

	rows = _parse_xlsx()
	_log(f"Parsed {len(rows)} rows from xlsx")

	errors = []
	imported = 0

	for row in rows:
		try:
			_import_supplier(row)
			imported += 1
		except Exception as e:
			errors.append(f"{row.get('Vendor Name', '?')}: {e}")
			frappe.db.rollback()

	frappe.db.commit()

	_log(f"\n{'='*50}")
	_log(f"Suppliers imported : {imported}")
	if errors:
		_log(f"Errors ({len(errors)}):")
		for err in errors:
			_log(f"  ✗ {err}")
	else:
		_log("All suppliers imported — zero errors")


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

def _setup_prerequisites():
	_log("\n--- Setting up prerequisites ---")
	_ensure_supplier_group(SUPPLIER_GROUP, "All Supplier Groups")
	frappe.db.commit()
	_log("Prerequisites ready")


def _ensure_supplier_group(name, parent):
	if frappe.db.exists("Supplier Group", name):
		return
	doc = frappe.new_doc("Supplier Group")
	doc.supplier_group_name = name
	doc.parent_supplier_group = parent
	doc.insert(ignore_permissions=True)
	_log(f"  Created Supplier Group: {name}")


# ---------------------------------------------------------------------------
# XLSX parsing
# ---------------------------------------------------------------------------

def _parse_xlsx():
	import openpyxl
	wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
	ws = wb.active
	headers = None
	rows = []
	for i, row in enumerate(ws.iter_rows(values_only=True)):
		if i == 0:
			headers = [str(h).strip() if h else "" for h in row]
			continue
		values = [c for c in row if c is not None]
		if not values:
			continue
		record = dict(zip(headers, row))
		if record.get("Vendor Name"):
			rows.append(record)
	return rows


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def _import_supplier(row):
	name      = str(row.get("Vendor Name", "")).strip()
	industry  = str(row.get("Industry Type", "") or "").strip()
	contact   = str(row.get("Contact Name", "") or "").strip()
	address   = " ".join(str(row.get("Address", "") or "").split())  # collapse newlines/extra spaces
	pincode   = str(row.get("Pin Code", "") or "").strip()
	city      = str(row.get("City", "") or "").strip()
	state     = _normalise_state(str(row.get("State", "") or "").strip())
	phone     = _clean_phone(row.get("Phone"))
	pan       = _clean_pan(row.get("PAN"))
	gstin     = str(row.get("GST", "") or "").strip()
	email     = str(row.get("E-mail", "") or "").strip()
	comments  = str(row.get("Comments", "") or "").strip()

	supplier_name = _import_supplier_doc(name, industry, pan, gstin, comments)
	_import_address(supplier_name, name, address, city, state, pincode, email, phone)
	_import_contact(supplier_name, contact, phone, email)

	_log(f"  ✓ {supplier_name}")


def _import_supplier_doc(name, industry, pan, gstin, comments):
	if frappe.db.exists("Supplier", name):
		_log(f"  → Supplier exists: {name}")
		return name

	doc = frappe.new_doc("Supplier")
	doc.supplier_name    = name
	doc.supplier_group   = SUPPLIER_GROUP
	doc.supplier_type    = "Company"
	doc.country          = COUNTRY
	doc.supplier_details = "\n".join(filter(None, [industry, comments]))

	if pan:
		doc.tax_id = pan

	if gstin:
		doc.gstin = gstin

	doc.insert(ignore_permissions=True)
	return doc.name


def _import_address(supplier_name, title, address_line1, city, state, pincode, email, phone):
	# Address autoname = {address_title}-{address_type}, so name = "{title}-Billing"
	expected_name = f"{title}-Billing"
	if frappe.db.exists("Address", expected_name):
		_log(f"    → Address exists: {expected_name}")
		return

	doc = frappe.new_doc("Address")
	doc.address_title      = title  # ERPNext appends "-{type}" automatically
	doc.address_type       = "Billing"
	doc.address_line1      = address_line1
	doc.city               = city
	doc.state              = state
	doc.pincode            = pincode
	doc.country            = COUNTRY
	doc.is_primary_address = 1

	if email:
		doc.email_id = email
	if phone:
		doc.phone = phone

	doc.append("links", {
		"link_doctype": "Supplier",
		"link_name":    supplier_name,
	})

	doc.insert(ignore_permissions=True)


def _import_contact(supplier_name, contact_name, phone, email):
	# Derive a stable contact ID: "<supplier_name>-Contact"
	contact_id = f"{supplier_name}-Contact"
	if frappe.db.exists("Contact", contact_id):
		_log(f"    → Contact exists: {contact_id}")
		return

	parts = contact_name.split(None, 1)
	first = parts[0] if parts else contact_name
	last  = parts[1] if len(parts) > 1 else ""

	doc = frappe.new_doc("Contact")
	doc.first_name = first
	doc.last_name  = last

	if email:
		doc.append("email_ids", {"email_id": email, "is_primary": 1})

	if phone:
		doc.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})

	doc.append("links", {
		"link_doctype": "Supplier",
		"link_name":    supplier_name,
	})

	doc.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATE_MAP = {s.upper(): s for s in [
	"Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
	"Bihar", "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu",
	"Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
	"Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
	"Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
	"Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
	"Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]}


def _normalise_state(val: str) -> str:
	return _STATE_MAP.get(val.upper(), val.title())


def _clean_phone(val) -> str:
	if val is None:
		return ""
	return str(val).replace(" ", "").strip()


def _clean_pan(val) -> str:
	if val is None:
		return ""
	s = str(val).strip()
	return "" if s in ("0", "0.0", "") else s


def _log(msg: str):
	print(msg)
	frappe.logger().info(f"[import_suppliers] {msg}")
