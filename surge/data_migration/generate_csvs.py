"""
Generate ERPNext Data Import CSVs for prod (Frappe Cloud — no terminal).
Run: bench --site <site> console → execfile("...generate_csvs.py")
  OR: bench --site <site> execute surge.data_migration.generate_csvs.run

Import order on prod:
  01_item_group_beer.csv     → Item Group  (Beer only — parent must exist first)
  02_item_group_sub.csv      → Item Group  (Beer - Lager, Beer - Wit)
  03_brands.csv              → Brand
  04_hsn_codes.csv           → GST HSN Code
  05_price_list.csv          → Price List
  06_volume_attribute.csv    → Item Attribute  (Volume + all values)
  ── Manual steps before 07 ─────────────────────────────────────────────
     a. Create Account: "Output VAT Goa" under Duties and Taxes
        Account Type: Tax | Tax Rate: 22%
     b. Create Item Tax Template: "Beer VAT Goa"
        GST Treatment: Non-GST
        Tax Row: Output VAT Goa @ 22%
  ───────────────────────────────────────────────────────────────────────
  07_item_templates.csv      → Item  (has_variants=1, no barcodes)
  08_item_variants.csv       → Item  (variant_of set, with barcodes)
  09_item_prices.csv         → Item Price
"""

import csv
import os
import frappe

OUT_DIR = "/home/ubuntu22/Downloads/surge_import_csvs"
COMPANY = "Karma Retail"
COMPANY_ABBR = "KRetail"
TAX_TEMPLATE = f"Beer VAT Goa - {COMPANY_ABBR}"


def run():
	os.makedirs(OUT_DIR, exist_ok=True)

	_gen_item_group_beer()
	_gen_item_group_sub()
	_gen_brands()
	_gen_hsn()
	_gen_price_list()
	_gen_volume_attribute()
	_gen_item_templates()
	_gen_item_variants()
	_gen_item_prices()
	_gen_readme()

	print(f"\nAll CSVs written to: {OUT_DIR}")


# ---------------------------------------------------------------------------

def _gen_item_group_beer():
	_write("01_item_group_beer.csv", [
		{"Item Group Name": "Beer", "Parent Item Group": "All Item Groups", "Is Group": 0},
	])


def _gen_item_group_sub():
	_write("02_item_group_sub.csv", [
		{"Item Group Name": "Beer - Lager", "Parent Item Group": "Beer", "Is Group": 0},
		{"Item Group Name": "Beer - Wit",   "Parent Item Group": "Beer", "Is Group": 0},
	])


def _gen_brands():
	brands = [
		"AMSTEL", "BUDWEISER", "CARLSBERG", "CORONA",
		"HEINEKEN", "HOEGAARDEN", "KING FISHER", "KRONENBOURG", "TUBORG",
	]
	_write("03_brands.csv", [{"Brand": b} for b in brands])


def _gen_hsn():
	_write("04_hsn_codes.csv", [
		{"HSN/SAC Code": "220300", "Description": "Beer made from malt"},
	])


def _gen_price_list():
	_write("05_price_list.csv", [
		{"Price List Name": "MRP", "Currency": "INR", "Selling": 1, "Buying": 0, "Enabled": 1},
	])


def _gen_volume_attribute():
	volumes = [
		("330 ML",     "330ML"),
		("330 ML Can", "330MLCan"),
		("500 ML",     "500ML"),
		("500 ML Can", "500MLCan"),
		("650 ML",     "650ML"),
	]
	row = {"ID": "Volume", "Attribute Name": "Volume", "Numeric Values": 0}
	for i, (val, abbr) in enumerate(volumes, start=1):
		row[f"item_attribute_values:Attribute Value:{i}"] = val
		row[f"item_attribute_values:Abbreviation:{i}"]    = abbr

	fields = ["ID", "Attribute Name", "Numeric Values"]
	for i in range(1, len(volumes) + 1):
		fields += [
			f"item_attribute_values:Attribute Value:{i}",
			f"item_attribute_values:Abbreviation:{i}",
		]
	_write("06_volume_attribute.csv", [row], fields)


def _gen_item_templates():
	templates = frappe.db.get_all(
		"Item",
		filters={"has_variants": 1},
		fields=["item_code", "item_name", "item_group", "brand", "stock_uom", "gst_hsn_code"],
		order_by="item_code asc",
	)

	rows = []
	for t in templates:
		rows.append({
			"ID":                        t.item_code,
			"Item Name":                 t.item_name,
			"Item Group":                t.item_group,
			"Brand":                     t.brand or "",
			"Default Unit of Measure":   t.stock_uom,
			"Is Stock Item":             1,
			"Has Variants":              1,
			"HSN/SAC Code":              t.gst_hsn_code or "220300",
			"GST Treatment":             "Non-GST",
			"Is Non GST":                1,
			"attributes:Attribute:1":    "Volume",
			"taxes:Item Tax Template:1": TAX_TEMPLATE,
			"item_defaults:Company:1":   COMPANY,
		})

	fields = [
		"ID", "Item Name", "Item Group", "Brand",
		"Default Unit of Measure", "Is Stock Item", "Has Variants",
		"HSN/SAC Code", "GST Treatment", "Is Non GST",
		"attributes:Attribute:1",
		"taxes:Item Tax Template:1",
		"item_defaults:Company:1",
	]
	_write("07_item_templates.csv", rows, fields)


def _gen_item_variants():
	variants = frappe.db.get_all(
		"Item",
		filters={"variant_of": ["!=", ""]},
		fields=["item_code", "item_name", "variant_of", "item_group",
		        "brand", "stock_uom", "gst_hsn_code"],
		order_by="variant_of asc, item_code asc",
	)

	# Fetch barcodes for all variants
	barcode_map: dict[str, list[tuple]] = {}
	barcodes = frappe.db.get_all(
		"Item Barcode",
		filters={"parent": ["in", [v.item_code for v in variants]]},
		fields=["parent", "barcode", "barcode_type"],
	)
	for b in barcodes:
		barcode_map.setdefault(b.parent, []).append((b.barcode, b.barcode_type or "EAN"))

	# Fetch volume attribute value for each variant
	attr_map: dict[str, str] = {}
	attrs = frappe.db.get_all(
		"Item Variant Attribute",
		filters={
			"parent": ["in", [v.item_code for v in variants]],
			"attribute": "Volume",
		},
		fields=["parent", "attribute_value"],
	)
	for a in attrs:
		attr_map[a.parent] = a.attribute_value

	rows = []
	max_barcodes = max((len(v) for v in barcode_map.values()), default=1)

	for v in variants:
		barcodes_list = barcode_map.get(v.item_code, [])
		row = {
			"ID":                        v.item_code,
			"Item Name":                 v.item_name,
			"Variant Of":                v.variant_of,
			"Item Group":                v.item_group,
			"Brand":                     v.brand or "",
			"Default Unit of Measure":   v.stock_uom,
			"Is Stock Item":             1,
			"HSN/SAC Code":              v.gst_hsn_code or "220300",
			"GST Treatment":             "Non-GST",
			"Is Non GST":                1,
			"attributes:Attribute:1":    "Volume",
			"attributes:Attribute Value:1": attr_map.get(v.item_code, ""),
			"taxes:Item Tax Template:1": TAX_TEMPLATE,
			"item_defaults:Company:1":   COMPANY,
		}
		for i, (barcode_val, barcode_type) in enumerate(barcodes_list, start=1):
			row[f"barcodes:Barcode:{i}"]      = barcode_val
			row[f"barcodes:Barcode Type:{i}"] = barcode_type

		rows.append(row)

	fields = [
		"ID", "Item Name", "Variant Of", "Item Group", "Brand",
		"Default Unit of Measure", "Is Stock Item",
		"HSN/SAC Code", "GST Treatment", "Is Non GST",
		"attributes:Attribute:1", "attributes:Attribute Value:1",
		"taxes:Item Tax Template:1",
		"item_defaults:Company:1",
	]
	for i in range(1, max_barcodes + 1):
		fields += [f"barcodes:Barcode:{i}", f"barcodes:Barcode Type:{i}"]

	_write("08_item_variants.csv", rows, fields)


def _gen_item_prices():
	prices = frappe.db.get_all(
		"Item Price",
		filters={"price_list": "MRP", "selling": 1},
		fields=["item_code", "price_list", "price_list_rate", "currency", "valid_from"],
		order_by="item_code asc",
	)
	rows = [{
		"Item Code":  p.item_code,
		"Price List": p.price_list,
		"Rate":       p.price_list_rate,
		"Currency":   p.currency,
		"Selling":    1,
		"Valid From": str(p.valid_from),
	} for p in prices]
	_write("09_item_prices.csv", rows)


def _gen_readme():
	content = """SURGE POS — Item Master Import Pack
=====================================

Import sequence (strict order — do NOT skip or reorder):

  1.  01_item_group_beer.csv   → DocType: Item Group
  2.  02_item_group_sub.csv    → DocType: Item Group
  3.  03_brands.csv            → DocType: Brand
  4.  04_hsn_codes.csv         → DocType: GST HSN Code
  5.  05_price_list.csv        → DocType: Price List
  6.  06_volume_attribute.csv  → DocType: Item Attribute

  ── Manual steps before 07 ──────────────────────────────────────────
     a. Create Account: "Output VAT Goa"
        Parent: Duties and Taxes | Account Type: Tax | Tax Rate: 22%
     b. Create Item Tax Template: "Beer VAT Goa"
        Company: Liquor Vault | GST Treatment: Non-GST
        Tax Row: Output VAT Goa @ 22%
  ────────────────────────────────────────────────────────────────────

  7.  07_item_templates.csv    → DocType: Item  (Import Type: Insert New Records)
  8.  08_item_variants.csv     → DocType: Item  (Import Type: Insert New Records)
  9.  09_item_prices.csv       → DocType: Item Price

Counts: 28 item templates | 55 variants | 55 prices | 9 brands

Open items — confirm with client before go-live:
  1. KF MANGO BERRY TWIST BEER 330 ML — two barcodes with different MRPs:
       8905002507019 @ Rs.75  |  8905002507033 @ Rs.85
     Imported at Rs.75. Confirm correct gazette MRP.

  2. BUDWEISER PREMIUM (650ML, Rs.130) vs BUDWEISER PREMIUM BEER (330ML/500ML)
     Treated as two separate templates due to inconsistent naming in xlsx.
     Confirm if same product — merge manually on prod if so.
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
