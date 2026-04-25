"""
Shared fixture bootstrap for Surge integration tests.

A fresh ERPNext site (bench new-site + install-app, no setup wizard) has zero
master data: no company, no warehouse, no UOM, no Modes of Payment, no HSN
codes, no Item/Customer/Territory groups.

ensure_master_data() creates the minimum set required by all test setUpClass
calls. Frappe wraps each test class in a DB SAVEPOINT, so this is called fresh
per class — idempotency checks (frappe.db.exists) make it safe.
"""

import frappe

# ── Constants used across all test files ────────────────────────────────────
TEST_COMPANY = "_Test Surge Co"
TEST_ABBR = "_TSC"
TEST_WAREHOUSE = f"Stores - {TEST_ABBR}"
TEST_ITEM_GROUP = "_Test Surge Item Group"
TEST_CUSTOMER_GROUP = "_Test Surge Customer Group"
TEST_TERRITORY = "_Test Surge Territory"
TEST_PRICE_LIST = "_Test Surge Price List"
TEST_HSN = "220300"  # 6 digits — india_compliance min_hsn_digits=6; Beer HSN


def ensure_master_data():
	_ensure_warehouse_types()
	_ensure_company()
	_ensure_uom()
	_ensure_item_group()
	_ensure_customer_group()
	_ensure_territory()
	_ensure_price_list()
	_ensure_modes_of_payment()
	_ensure_hsn()
	frappe.db.commit()


# ── Internals ────────────────────────────────────────────────────────────────


def _ensure_warehouse_types():
	# ERPNext create_default_warehouses() sets warehouse_type="Transit" on the
	# "Goods In Transit" warehouse. Warehouse Type uses autoname=Prompt so name
	# must be set explicitly. Fresh sites have no Warehouse Type records.
	if not frappe.db.exists("Warehouse Type", "Transit"):
		wt = frappe.new_doc("Warehouse Type")
		wt.name = "Transit"
		wt.insert(ignore_permissions=True)


def _ensure_company():
	if not frappe.db.exists("Company", TEST_COMPANY):
		c = frappe.new_doc("Company")
		c.company_name = TEST_COMPANY
		c.abbr = TEST_ABBR
		c.default_currency = "INR"
		c.country = "India"
		c.insert(ignore_permissions=True)
		# after_insert creates the full Indian Chart of Accounts (Cash - _TSC, etc.)
		frappe.db.commit()

	if frappe.db.get_single_value("Global Defaults", "default_company") != TEST_COMPANY:
		frappe.db.set_single_value("Global Defaults", "default_company", TEST_COMPANY)

	if not frappe.db.exists("Warehouse", TEST_WAREHOUSE):
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = "Stores"
		wh.company = TEST_COMPANY
		wh.insert(ignore_permissions=True)


def _ensure_uom():
	if not frappe.db.exists("UOM", "Nos"):
		u = frappe.new_doc("UOM")
		u.uom_name = "Nos"
		u.insert(ignore_permissions=True)


def _ensure_item_group():
	if not frappe.db.exists("Item Group", TEST_ITEM_GROUP):
		# ERPNext requires a root "All Item Groups" parent
		if not frappe.db.exists("Item Group", "All Item Groups"):
			root = frappe.new_doc("Item Group")
			root.item_group_name = "All Item Groups"
			root.is_group = 1
			root.insert(ignore_permissions=True)
		g = frappe.new_doc("Item Group")
		g.item_group_name = TEST_ITEM_GROUP
		g.parent_item_group = "All Item Groups"
		g.is_group = 0
		g.insert(ignore_permissions=True)


def _ensure_customer_group():
	if not frappe.db.exists("Customer Group", TEST_CUSTOMER_GROUP):
		if not frappe.db.exists("Customer Group", "All Customer Groups"):
			root = frappe.new_doc("Customer Group")
			root.customer_group_name = "All Customer Groups"
			root.is_group = 1
			root.insert(ignore_permissions=True)
		g = frappe.new_doc("Customer Group")
		g.customer_group_name = TEST_CUSTOMER_GROUP
		g.parent_customer_group = "All Customer Groups"
		g.is_group = 0
		g.insert(ignore_permissions=True)


def _ensure_territory():
	if not frappe.db.exists("Territory", TEST_TERRITORY):
		if not frappe.db.exists("Territory", "All Territories"):
			root = frappe.new_doc("Territory")
			root.territory_name = "All Territories"
			root.is_group = 1
			root.insert(ignore_permissions=True)
		t = frappe.new_doc("Territory")
		t.territory_name = TEST_TERRITORY
		t.parent_territory = "All Territories"
		t.is_group = 0
		t.insert(ignore_permissions=True)


def _ensure_price_list():
	if not frappe.db.exists("Price List", TEST_PRICE_LIST):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = TEST_PRICE_LIST
		pl.selling = 1
		pl.buying = 0
		pl.currency = "INR"
		pl.insert(ignore_permissions=True)


def _ensure_modes_of_payment():
	# POS Profile validator (ERPNext v16) requires each MoP to have a
	# Mode of Payment Account row for the company — the account must be Cash/Bank type.
	cash_account = frappe.db.get_value(
		"Account",
		{"company": TEST_COMPANY, "account_type": "Cash", "is_group": 0},
		"name",
	)

	for mop_name, mop_type in [("Cash", "Cash"), ("UPI", "General")]:
		if not frappe.db.exists("Mode of Payment", mop_name):
			m = frappe.new_doc("Mode of Payment")
			m.mode_of_payment = mop_name
			m.type = mop_type
			m.insert(ignore_permissions=True)

		if cash_account and not frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": mop_name, "company": TEST_COMPANY},
		):
			m = frappe.get_doc("Mode of Payment", mop_name)
			m.append("accounts", {"company": TEST_COMPANY, "default_account": cash_account})
			m.save(ignore_permissions=True)


def _ensure_hsn():
	if not frappe.db.exists("GST HSN Code", TEST_HSN):
		h = frappe.new_doc("GST HSN Code")
		h.hsn_code = TEST_HSN
		h.description = "Beer made from malt"
		h.insert(ignore_permissions=True)
