"""
Item Master Import — 3 Brands Product Master

Run:
  bench --site <site> execute \
    "from surge.data_migration.import_items import run; run()"

India Compliance note:
  Items are Non-GST (Goa liquor). No Item Tax Template is used on items.
  Goa VAT @ 22% is applied at the POS Profile level via Sales Taxes and
  Charges Template — NOT at the item level.
"""

import re

import frappe
from frappe.utils import nowdate

XLSX_PATH = "/home/ubuntu22/Downloads/3 Brands - Product Master.xlsx"

COMPANY = "Liquor Vault"
COMPANY_ABBR = "LV"
WAREHOUSE = "Stores - LV"
INCOME_ACCOUNT = "Sales - LV"
EXPENSE_ACCOUNT = "Cost of Goods Sold - LV"
COST_CENTER = "Main - LV"

HSN_CODE = "220300"
HSN_DESC = "Beer made from malt"
PRICE_LIST = "MRP"
VOLUME_ATTRIBUTE = "Volume"
TAX_TEMPLATE_TITLE = "Beer VAT Goa"
VAT_ACCOUNT = "Output VAT Goa - LV"
VAT_RATE = 22.0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run():
	_log("Starting item master import")

	_setup_prerequisites()

	rows = _parse_xlsx()
	_log(f"Parsed {len(rows)} rows from xlsx")

	templates = _group_into_templates(rows)
	_log(f"Grouped into {len(templates)} item templates")

	errors = []
	imported_templates = 0
	imported_variants = 0

	for tpl in templates:
		try:
			created_variants = _import_template(tpl)
			imported_templates += 1
			imported_variants += created_variants
		except Exception as e:
			errors.append(f"Template '{tpl['template_name']}': {e}")
			frappe.db.rollback()

	frappe.db.commit()  # nosemgrep: frappe-manual-commit — batch migration commits required for memory management and rollback isolation

	_log(f"\n{'=' * 50}")
	_log(f"Templates imported : {imported_templates}")
	_log(f"Variants imported  : {imported_variants}")
	if errors:
		_log(f"Errors ({len(errors)}):")
		for err in errors:
			_log(f"  ✗ {err}")
	else:
		_log("All items imported successfully — zero errors")


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------


def _setup_prerequisites():
	_log("\n--- Setting up prerequisites ---")
	_ensure_item_group("Beer", "All Item Groups")
	_ensure_item_group("Beer - Lager", "Beer")
	_ensure_item_group("Beer - Wit", "Beer")
	_ensure_hsn_code(HSN_CODE, HSN_DESC)
	_ensure_price_list(PRICE_LIST)
	_ensure_vat_account()
	_ensure_item_tax_template()
	_ensure_volume_attribute()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — batch migration commits required for memory management and rollback isolation
	_log("Prerequisites ready")


def _ensure_item_group(group_name, parent):
	if frappe.db.exists("Item Group", group_name):
		return
	doc = frappe.new_doc("Item Group")
	doc.item_group_name = group_name
	doc.parent_item_group = parent
	doc.insert(ignore_permissions=True)
	_log(f"  Created Item Group: {group_name}")


def _ensure_hsn_code(code, description):
	if frappe.db.exists("GST HSN Code", code):
		return
	doc = frappe.new_doc("GST HSN Code")
	doc.hsn_code = code
	doc.description = description
	doc.insert(ignore_permissions=True)
	_log(f"  Created HSN Code: {code}")


def _ensure_price_list(name):
	if frappe.db.exists("Price List", name):
		return
	doc = frappe.new_doc("Price List")
	doc.price_list_name = name
	doc.currency = "INR"
	doc.selling = 1
	doc.buying = 0
	doc.enabled = 1
	doc.insert(ignore_permissions=True)
	_log(f"  Created Price List: {name}")


def _ensure_vat_account():
	if frappe.db.exists("Account", VAT_ACCOUNT):
		return
	parent = frappe.db.get_value(
		"Account",
		{"account_name": "Duties and Taxes", "company": COMPANY},
		"name",
	)
	doc = frappe.new_doc("Account")
	doc.account_name = "Output VAT Goa"
	doc.parent_account = parent
	doc.company = COMPANY
	doc.account_type = "Tax"
	doc.tax_rate = VAT_RATE
	doc.insert(ignore_permissions=True)
	_log(f"  Created Account: {VAT_ACCOUNT}")


def _ensure_item_tax_template():
	template_name = f"{TAX_TEMPLATE_TITLE} - {COMPANY_ABBR}"
	if frappe.db.exists("Item Tax Template", template_name):
		return
	doc = frappe.new_doc("Item Tax Template")
	doc.title = TAX_TEMPLATE_TITLE
	doc.company = COMPANY
	doc.gst_treatment = "Non-GST"
	doc.append(
		"taxes",
		{
			"tax_type": VAT_ACCOUNT,
			"tax_rate": VAT_RATE,
		},
	)
	doc.insert(ignore_permissions=True)
	_log(f"  Created Item Tax Template: {template_name}")


def _ensure_volume_attribute():
	all_volumes = {
		"330 ML",
		"500 ML",
		"650 ML",
		"330 ML Can",
		"500 ML Can",
	}
	if frappe.db.exists("Item Attribute", VOLUME_ATTRIBUTE):
		doc = frappe.get_doc("Item Attribute", VOLUME_ATTRIBUTE)
		existing = {r.attribute_value for r in doc.item_attribute_values}
		missing = all_volumes - existing
		if missing:
			for val in sorted(missing):
				doc.append(
					"item_attribute_values",
					{
						"attribute_value": val,
						"abbr": val.replace(" ", "")[:8],
					},
				)
			doc.save(ignore_permissions=True)
			_log(f"  Added Volume values: {missing}")
		return

	doc = frappe.new_doc("Item Attribute")
	doc.attribute_name = VOLUME_ATTRIBUTE
	doc.numeric_values = 0
	for val in sorted(all_volumes):
		doc.append(
			"item_attribute_values",
			{
				"attribute_value": val,
				"abbr": val.replace(" ", "")[:8],
			},
		)
	doc.insert(ignore_permissions=True)
	_log(f"  Created Item Attribute: {VOLUME_ATTRIBUTE}")


def _ensure_brand(brand_name):
	if frappe.db.exists("Brand", brand_name):
		return
	doc = frappe.new_doc("Brand")
	doc.brand = brand_name
	doc.insert(ignore_permissions=True)


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
		# Stop at first fully-empty row
		values = [c for c in row if c is not None]
		if not values:
			continue
		record = dict(zip(headers, row, strict=False))
		# Only keep rows that have at least a variation name
		if not record.get("VARIATION NAME"):
			continue
		rows.append(record)
	return rows


# ---------------------------------------------------------------------------
# Template grouping
# ---------------------------------------------------------------------------

_TYPO_CORRECTIONS = {
	"ELEPHENT": "ELEPHANT",
}

_SUBCATEGORY_GROUP_MAP = {
	"LAGER": "Beer - Lager",
	"WIT": "Beer - Wit",
}


def _normalise_name(name: str) -> str:
	for wrong, right in _TYPO_CORRECTIONS.items():
		name = name.replace(wrong, right)
	return name.strip()


def _extract_template_and_volume(variation_name: str, ml_gms: str):
	"""
	Extracts (template_name, volume_attribute_value) from a row.

	Rules:
	  - "{product} {vol} CAN" at end  → CAN is packaging variant
	    template = product, volume = "{vol} Can"
	  - "{product} CAN {vol}" pattern → CAN is part of product name
	    template = "{product} CAN", volume = vol
	  - "{product} {vol}"             → straightforward
	    template = product, volume = vol
	"""
	ml_num = ml_gms.strip().split()[0]  # "330", "500", "650"
	name = _normalise_name(variation_name)

	# Pattern A: volume then CAN at end  e.g. "CORONA BEER 500 ML CAN"
	pat_vol_then_can = re.compile(rf"\s+{ml_num}\s*(?:ML|GMS)\s+CAN\s*$", re.IGNORECASE)
	if pat_vol_then_can.search(name):
		template = pat_vol_then_can.sub("", name).strip()
		return template, f"{ml_num} ML Can"

	# Pattern B: volume at end (with or without space before ML)
	pat_vol = re.compile(rf"\s+{ml_num}\s*(?:ML|GMS)\s*$", re.IGNORECASE)
	if pat_vol.search(name):
		template = pat_vol.sub("", name).strip()
		return template, ml_gms.strip()

	# Fallback: return as-is with volume from column
	return name, ml_gms.strip()


def _group_into_templates(rows):
	"""
	Returns list of template dicts:
	{
	  template_name, brand, item_group, variants: [
	    { volume, sku, mrp, barcodes: [...] }
	  ]
	}
	"""
	templates: dict = {}

	for row in rows:
		brand = str(row.get("BRAND NAME", "")).strip()
		variation = str(row.get("VARIATION NAME", "")).strip()
		sub_cat = str(row.get("SUB \nCATEGORY", "") or "").strip().upper()
		ml_gms = str(row.get("ML/GMS", "")).strip()
		sku = row.get("ITEM SKU")
		mrp = float(row.get("MRP") or 0)

		item_group = _SUBCATEGORY_GROUP_MAP.get(sub_cat, "Beer - Lager")
		template_name, volume = _extract_template_and_volume(variation, ml_gms)

		key = (template_name, brand)

		if key not in templates:
			templates[key] = {
				"template_name": template_name,
				"brand": brand,
				"item_group": item_group,
				"variants": {},
			}

		# Deduplicate by volume — same volume can have multiple barcodes
		variant_key = volume
		barcode_info = _classify_sku(sku)

		if variant_key not in templates[key]["variants"]:
			templates[key]["variants"][variant_key] = {
				"volume": volume,
				"mrp": mrp,
				"barcodes": [barcode_info] if barcode_info else [],
				"mrp_conflict": False,
			}
		else:
			existing = templates[key]["variants"][variant_key]
			if barcode_info:
				existing_vals = [b[0] for b in existing["barcodes"]]
				if barcode_info[0] not in existing_vals:
					existing["barcodes"].append(barcode_info)
			# Flag MRP conflict — different MRP for same variant
			if abs(existing["mrp"] - mrp) > 0.01:
				_log(
					f"  ⚠ MRP conflict for '{template_name}' [{volume}]: "
					f"existing ₹{existing['mrp']}, new ₹{mrp} "
					f"(SKU {sku}) — keeping existing MRP"
				)
				existing["mrp_conflict"] = True

	# Flatten to list
	result = []
	for tpl in templates.values():
		tpl["variants"] = list(tpl["variants"].values())
		result.append(tpl)

	return result


def _classify_sku(sku):
	"""Returns (barcode_str, barcode_type) or None if SKU is absent/invalid."""
	if sku is None:
		return None
	s = str(int(sku)) if isinstance(sku, float) else str(sku).strip()
	if not s:
		return None
	if s.isdigit() and len(s) >= 8:
		return (s, "EAN")
	return (s, "CODE-39")


# ---------------------------------------------------------------------------
# Item import
# ---------------------------------------------------------------------------


def _import_template(tpl: dict) -> int:
	template_name = tpl["template_name"]
	brand = tpl["brand"]
	item_group = tpl["item_group"]
	variants = tpl["variants"]

	_ensure_brand(brand)
	tax_template = f"{TAX_TEMPLATE_TITLE} - {COMPANY_ABBR}"

	if not frappe.db.exists("Item", template_name):
		template_doc = frappe.new_doc("Item")
		template_doc.item_code = template_name
		template_doc.item_name = template_name
		template_doc.item_group = item_group
		template_doc.brand = brand
		template_doc.stock_uom = "Nos"
		template_doc.is_stock_item = 1
		template_doc.has_variants = 1
		template_doc.gst_hsn_code = HSN_CODE
		template_doc.gst_treatment = "Non-GST"
		template_doc.is_non_gst = 1

		template_doc.append("attributes", {"attribute": VOLUME_ATTRIBUTE})

		template_doc.append("taxes", {"item_tax_template": tax_template})

		template_doc.append(
			"item_defaults",
			{
				"company": COMPANY,
				"default_warehouse": WAREHOUSE,
				"income_account": INCOME_ACCOUNT,
				"expense_account": EXPENSE_ACCOUNT,
				"cost_center": COST_CENTER,
			},
		)

		template_doc.insert(ignore_permissions=True)
		_log(f"  ✓ Template: {template_name}")
	else:
		_log(f"  → Template exists: {template_name}")

	created = 0
	for var in variants:
		try:
			_import_variant(template_name, var)
			created += 1
		except Exception as e:
			_log(f"    ✗ Variant [{var['volume']}]: {e}")
			frappe.db.rollback()

	return created


def _import_variant(template_code: str, var: dict):
	from erpnext.controllers.item_variant import create_variant

	volume = var["volume"]
	mrp = var["mrp"]
	barcodes = var["barcodes"]

	# Check if variant already exists for this template + volume
	existing_variant = frappe.db.get_value(
		"Item Variant Attribute",
		{
			"parent": ["like", f"{template_code}%"],
			"attribute": VOLUME_ATTRIBUTE,
			"attribute_value": volume,
		},
		"parent",
	)

	if existing_variant:
		_log(f"    → Variant exists: {existing_variant} [{volume}]")
		return

	# Use ERPNext's variant controller — respects all template-level validations
	variant_doc = create_variant(template_code, {VOLUME_ATTRIBUTE: volume})

	# Variant-level overrides — template values are inherited via create_variant
	variant_doc.gst_treatment = "Non-GST"
	variant_doc.is_non_gst = 1

	# Clear auto-inherited barcodes and set from xlsx
	variant_doc.barcodes = []
	for barcode_val, barcode_type in barcodes:
		variant_doc.append(
			"barcodes",
			{
				"barcode": barcode_val,
				"barcode_type": barcode_type,
			},
		)

	variant_doc.insert(ignore_permissions=True)

	# Item Price — MRP price list (tax-inclusive rate = MRP)
	_create_item_price(variant_doc.item_code, mrp)

	_log(f"    ✓ Variant: {variant_doc.item_code} [{volume}] MRP ₹{mrp}")


def _create_item_price(item_code: str, rate: float):
	if frappe.db.exists(
		"Item Price",
		{
			"item_code": item_code,
			"price_list": PRICE_LIST,
			"selling": 1,
		},
	):
		return

	doc = frappe.new_doc("Item Price")
	doc.item_code = item_code
	doc.price_list = PRICE_LIST
	doc.selling = 1
	doc.currency = "INR"
	doc.price_list_rate = rate
	doc.valid_from = nowdate()
	doc.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Patch: add Code128 barcodes to existing items that had alphanumeric SKUs
# ---------------------------------------------------------------------------


def patch_code128_barcodes():
	"""
	One-time patch: add Code128 barcodes for variants created without one
	because their xlsx SKU was alphanumeric (e.g. LV2024001).
	Safe to re-run — skips already-present barcodes.
	"""
	_log("Patching Code128 barcodes...")
	rows = _parse_xlsx()
	patched = 0

	for row in rows:
		sku = row.get("ITEM SKU")
		bc = _classify_sku(sku)
		if bc is None or bc[1] == "EAN":
			continue

		barcode_val, barcode_type = bc
		variation = str(row.get("VARIATION NAME", "")).strip()
		ml_gms = str(row.get("ML/GMS", "")).strip()
		template_name, volume = _extract_template_and_volume(variation, ml_gms)

		variant_code = frappe.db.get_value(
			"Item Variant Attribute",
			{
				"parent": ["like", f"{template_name}%"],
				"attribute": VOLUME_ATTRIBUTE,
				"attribute_value": volume,
			},
			"parent",
		)
		if not variant_code:
			_log(f"  ✗ Variant not found: {template_name} [{volume}]")
			continue

		if frappe.db.exists("Item Barcode", {"parent": variant_code, "barcode": barcode_val}):
			_log(f"  → Already present: {variant_code} [{barcode_val}]")
			continue

		doc = frappe.get_doc("Item", variant_code)
		doc.append("barcodes", {"barcode": barcode_val, "barcode_type": barcode_type})
		doc.save(ignore_permissions=True)
		_log(f"  ✓ {variant_code} ← {barcode_type} {barcode_val}")
		patched += 1

	frappe.db.commit()  # nosemgrep: frappe-manual-commit — batch migration commits required for memory management and rollback isolation
	_log(f"Patched {patched} barcodes")


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------


def _log(msg: str):
	print(msg)
	frappe.logger().info(f"[import_items] {msg}")
