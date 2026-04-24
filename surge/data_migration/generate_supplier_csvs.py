"""
Generate ERPNext Data Import CSVs for supplier master (Frappe Cloud prod).
Run: bench --site <site> execute surge.data_migration.generate_supplier_csvs.run

Import order on prod:
  01_supplier_group.csv   → Supplier Group
  02_suppliers.csv        → Supplier
  03_supplier_addresses.csv → Address
  04_supplier_contacts.csv  → Contact
"""

import csv
import os
import frappe

OUT_DIR = "/home/ubuntu22/Downloads/surge_supplier_csvs"
SUPPLIER_GROUP = "Wholesale"


def run():
	os.makedirs(OUT_DIR, exist_ok=True)

	_gen_supplier_group()
	_gen_suppliers()
	_gen_addresses()
	_gen_contacts()
	_gen_readme()

	print(f"\nAll CSVs written to: {OUT_DIR}")


# ---------------------------------------------------------------------------

def _gen_supplier_group():
	_write("01_supplier_group.csv", [
		{
			"Supplier Group Name": SUPPLIER_GROUP,
			"Parent Supplier Group": "All Supplier Groups",
			"Is Group": 0,
		}
	])


def _gen_suppliers():
	suppliers = frappe.db.get_all(
		"Supplier",
		filters={"supplier_group": SUPPLIER_GROUP},
		fields=["name", "supplier_name", "supplier_group", "supplier_type",
		        "tax_id", "gstin", "supplier_details", "country"],
		order_by="name asc",
	)
	rows = [{
		"ID":             s.name,
		"Supplier Name":  s.supplier_name,
		"Supplier Group": s.supplier_group,
		"Supplier Type":  s.supplier_type or "Company",
		"Tax ID":         s.tax_id or "",
		"GSTIN":          s.gstin or "",
		"Supplier Details": s.supplier_details or "",
		"Country":        s.country or "India",
	} for s in suppliers]
	_write("02_suppliers.csv", rows)


def _gen_addresses():
	# Fetch addresses linked to our suppliers via Dynamic Link
	supplier_names = frappe.db.get_all(
		"Supplier",
		filters={"supplier_group": SUPPLIER_GROUP},
		pluck="name",
	)

	addresses = frappe.db.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "in", supplier_names],
		],
		fields=["name", "address_title", "address_type", "address_line1",
		        "city", "state", "pincode", "country", "email_id",
		        "phone", "is_primary_address"],
		order_by="name asc",
	)

	rows = []
	for a in addresses:
		# Resolve which supplier this address is linked to
		link = frappe.db.get_value(
			"Dynamic Link",
			{"parent": a.name, "link_doctype": "Supplier"},
			"link_name",
		)
		rows.append({
			"ID":                     a.name,
			"Address Title":          a.address_title,
			"Address Type":           a.address_type,
			"Address Line 1":         a.address_line1 or "",
			"City/Town":              a.city or "",
			"State/Province":         a.state or "",
			"Postal Code":            a.pincode or "",
			"Country":                a.country or "India",
			"Email Address":          a.email_id or "",
			"Phone":                  a.phone or "",
			"Preferred Billing Address": 1 if a.is_primary_address else 0,
			"links:Link DocType:1":   "Supplier",
			"links:Link Name:1":      link or "",
		})

	fields = [
		"ID", "Address Title", "Address Type", "Address Line 1",
		"City/Town", "State/Province", "Postal Code", "Country",
		"Email Address", "Phone", "Preferred Billing Address",
		"links:Link DocType:1", "links:Link Name:1",
	]
	_write("03_supplier_addresses.csv", rows, fields)


def _gen_contacts():
	supplier_names = frappe.db.get_all(
		"Supplier",
		filters={"supplier_group": SUPPLIER_GROUP},
		pluck="name",
	)

	contacts = frappe.db.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "in", supplier_names],
		],
		fields=["name", "first_name", "last_name", "mobile_no", "email_id"],
		order_by="name asc",
	)

	rows = []
	for c in contacts:
		link = frappe.db.get_value(
			"Dynamic Link",
			{"parent": c.name, "link_doctype": "Supplier"},
			"link_name",
		)
		# Fetch primary email from email_ids child table
		primary_email = frappe.db.get_value(
			"Contact Email",
			{"parent": c.name, "is_primary": 1},
			"email_id",
		) or c.email_id or ""

		# Fetch primary phone from phone_nos child table
		primary_phone = frappe.db.get_value(
			"Contact Phone",
			{"parent": c.name, "is_primary_mobile_no": 1},
			"phone",
		) or c.mobile_no or ""

		rows.append({
			"ID":                        c.name,
			"First Name":                c.first_name or "",
			"Last Name":                 c.last_name or "",
			"email_ids:Email Id:1":      primary_email,
			"email_ids:Is Primary:1":    1,
			"phone_nos:Phone:1":         primary_phone,
			"phone_nos:Is Primary Mobile No:1": 1,
			"links:Link DocType:1":      "Supplier",
			"links:Link Name:1":         link or "",
		})

	fields = [
		"ID", "First Name", "Last Name",
		"email_ids:Email Id:1", "email_ids:Is Primary:1",
		"phone_nos:Phone:1", "phone_nos:Is Primary Mobile No:1",
		"links:Link DocType:1", "links:Link Name:1",
	]
	_write("04_supplier_contacts.csv", rows, fields)


def _gen_readme():
	content = """SURGE POS — Supplier Master Import Pack
=========================================

Import sequence (strict order):

  1. 01_supplier_group.csv      → DocType: Supplier Group
  2. 02_suppliers.csv           → DocType: Supplier
  3. 03_supplier_addresses.csv  → DocType: Address
  4. 04_supplier_contacts.csv   → DocType: Contact

Notes:
  - GSTIN is a field added by India Compliance. If it does not appear
    in the column mapping, set it manually on each supplier after import
    (only 3 suppliers).
  - State in addresses must match India Compliance's state list exactly
    (e.g. "Goa", not "GOA").
  - Address links to Supplier via links:Link DocType / links:Link Name
    columns — map these to "Link DocType (Links)" and "Link Name (Links)"
    in the Data Import column mapper.
"""
	with open(os.path.join(OUT_DIR, "README.txt"), "w") as f:
		f.write(content)
	print("  README.txt")


# ---------------------------------------------------------------------------

def _write(filename: str, rows: list, fields: list | None = None):
	path = os.path.join(OUT_DIR, filename)
	if not rows:
		print(f"  {filename} — 0 rows, skipped")
		return
	if fields is None:
		fields = list(rows[0].keys())
	with open(path, "w", newline="", encoding="utf-8") as f:
		w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
		w.writeheader()
		w.writerows(rows)
	print(f"  {filename} — {len(rows)} rows")
