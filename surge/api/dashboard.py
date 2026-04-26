import frappe

from surge.utils.json import surge_response


def _can(doctype: str, ptype: str = "read") -> int:
	try:
		return 1 if frappe.has_permission(doctype, ptype) else 0
	except Exception:
		return 0


@frappe.whitelist(allow_guest=False)
def is_manager() -> object:
	exists = frappe.db.exists(
		"POS Profile User",
		{
			"user": frappe.session.user,
			"access_level": ["in", ["Manager", "Supervisor"]],
			"status": "Active",
		},
	)
	return surge_response({"is_manager": bool(exists)})


@frappe.whitelist(allow_guest=False)
def get_sidebar_permissions() -> object:
	return surge_response(
		{
			"item_read": _can("Item"),
			"item_create": _can("Item", "create"),
			"item_group_create": _can("Item Group", "create"),
			"brand_create": _can("Brand", "create"),
			"stock_ledger_read": _can("Stock Ledger Entry"),
			"bin_read": _can("Bin"),
			"purchase_order_read": _can("Purchase Order"),
			"purchase_receipt_read": _can("Purchase Receipt"),
			"sales_invoice_read": _can("Sales Invoice"),
			"warehouse_read": _can("Warehouse"),
			"customer_read": _can("Customer"),
			"supplier_read": _can("Supplier"),
			"pos_profile_read": _can("POS Profile"),
		}
	)


@frappe.whitelist(allow_guest=False)
def get_dashboard_stats(from_date: str, to_date: str) -> object:
	_require_manager()

	company = frappe.defaults.get_user_default("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)

	cache_key = f"surge:dashboard:stats:v2:{company}:{from_date}:{to_date}"
	cached = frappe.cache().get_value(cache_key)
	if cached:
		return surge_response(cached)

	values = {"company": company, "from_date": from_date, "to_date": to_date}

	# ── Sales KPIs (POS-only: is_pos=1) ────────────────────────────────────────
	# Surge sets is_pos=1 on every invoice it creates. Filtering here ensures
	# desk-created credit sales or service invoices never corrupt POS metrics.
	si_row = frappe.db.sql(
		"""
        SELECT
            SUM(CASE WHEN is_return = 0 THEN grand_total ELSE 0 END)        AS total_sales,
            SUM(CASE WHEN is_return = 1 THEN ABS(grand_total) ELSE 0 END)   AS total_returns,
            COUNT(CASE WHEN is_return = 0 THEN 1 END)                       AS invoice_count,
            SUM(CASE WHEN is_return = 0 THEN outstanding_amount ELSE 0 END) AS outstanding
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND is_pos     = 1
          AND company    = %(company)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        """,
		values,
		as_dict=True,
	)[0]

	# ── Purchase KPIs ────────────────────────────────────────────────────────────
	pr_row = frappe.db.sql(
		"""
        SELECT
            SUM(CASE WHEN is_return = 0 THEN grand_total ELSE 0 END)      AS total_purchase,
            SUM(CASE WHEN is_return = 1 THEN ABS(grand_total) ELSE 0 END) AS purchase_returns
        FROM `tabPurchase Receipt`
        WHERE docstatus = 1
          AND company   = %(company)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        """,
		values,
		as_dict=True,
	)[0]

	# ── Expenses (GL) ────────────────────────────────────────────────────────────
	exp_row = frappe.db.sql(
		"""
        SELECT COALESCE(SUM(debit - credit), 0) AS expenses
        FROM `tabGL Entry`
        WHERE is_cancelled = 0
          AND company      = %(company)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND account IN (
              SELECT name FROM `tabAccount`
              WHERE root_type = 'Expense' AND company = %(company)s
          )
        """,
		values,
		as_dict=True,
	)[0]

	# ── Overview counts ──────────────────────────────────────────────────────────
	customer_count = frappe.db.count("Customer")
	supplier_count = frappe.db.count("Supplier")
	pos_open_count = frappe.db.count(
		"POS Opening Entry",
		{"company": company, "docstatus": 1, "period_start_date": ["between", [from_date, to_date]]},
	)

	# ── Recent transactions (POS-only) ──────────────────────────────────────────
	recent = frappe.db.sql(
		"""
        SELECT name, customer, posting_date, status, grand_total, is_return
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND is_pos    = 1
          AND company   = %(company)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY creation DESC
        LIMIT 10
        """,
		values,
		as_dict=True,
	)

	# ── Top selling products (POS-only) ─────────────────────────────────────────
	top_products = frappe.db.sql(
		"""
        SELECT sii.item_code, sii.item_name,
               SUM(sii.qty)        AS total_qty,
               SUM(sii.net_amount) AS total_amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
          AND si.is_pos     = 1
          AND si.is_return  = 0
          AND si.company    = %(company)s
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY sii.item_code, sii.item_name
        ORDER BY total_qty DESC
        LIMIT 5
        """,
		values,
		as_dict=True,
	)

	# ── Low-stock items ──────────────────────────────────────────────────────────
	low_stock = frappe.db.sql(
		"""
        SELECT b.item_code, i.item_name, b.warehouse,
               b.actual_qty, COALESCE(ir.warehouse_reorder_level, 0) AS reorder_level,
               COALESCE(ir.warehouse_reorder_qty, 0)                 AS reorder_qty
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code AND i.disabled = 0
        LEFT JOIN `tabItem Reorder` ir ON ir.parent = b.item_code AND ir.warehouse = b.warehouse
        WHERE b.actual_qty <= COALESCE(ir.warehouse_reorder_level, 0)
          AND b.actual_qty >= 0
        ORDER BY (b.actual_qty - COALESCE(ir.warehouse_reorder_level, 0)) ASC
        LIMIT 10
        """,
		as_dict=True,
	)

	total_sales = float(si_row.total_sales or 0)
	total_purchase = float(pr_row.total_purchase or 0)
	profit = total_sales - total_purchase

	company_currency = frappe.db.get_value("Company", company, "default_currency") or "INR"
	currency_symbol = frappe.db.get_value("Currency", company_currency, "symbol") or "₹"

	result = {
		"currency_symbol": currency_symbol,
		"kpi": {
			"total_sales": total_sales,
			"total_returns": float(si_row.total_returns or 0),
			"total_purchase": total_purchase,
			"purchase_returns": float(pr_row.purchase_returns or 0),
			"profit": profit,
			"outstanding": float(si_row.outstanding or 0),
			"expenses": float(exp_row.expenses or 0),
			"invoice_count": int(si_row.invoice_count or 0),
		},
		"overview": {
			"customers": customer_count,
			"suppliers": supplier_count,
			"pos_sessions": pos_open_count,
		},
		"recent_transactions": [
			{
				"name": r.name,
				"customer": r.customer,
				"posting_date": str(r.posting_date),
				"status": r.status,
				"grand_total": float(r.grand_total or 0),
				"is_return": bool(r.is_return),
			}
			for r in recent
		],
		"top_products": [
			{
				"item_code": p.item_code,
				"item_name": p.item_name,
				"total_qty": float(p.total_qty or 0),
				"total_amount": float(p.total_amount or 0),
			}
			for p in top_products
		],
		"low_stock": [
			{
				"item_code": s.item_code,
				"item_name": s.item_name,
				"warehouse": s.warehouse,
				"actual_qty": float(s.actual_qty or 0),
				"reorder_level": float(s.reorder_level or 0),
				"reorder_qty": float(s.reorder_qty or 0),
			}
			for s in low_stock
		],
	}

	frappe.cache().set_value(cache_key, result, expires_in_sec=300)
	return surge_response(result)


@frappe.whitelist(allow_guest=False)
def get_chart_data(period: str = "1M") -> object:
	_require_manager()

	company = frappe.defaults.get_user_default("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)

	period_map = {
		"1D": ("DATE_FORMAT(posting_date, '%%H:00')", "1 DAY"),
		"1W": ("DATE_FORMAT(posting_date, '%%a')", "7 DAY"),
		"1M": ("DATE_FORMAT(posting_date, '%%d %%b')", "30 DAY"),
		"3M": ("DATE_FORMAT(posting_date, '%%b %%Y')", "90 DAY"),
		"6M": ("DATE_FORMAT(posting_date, '%%b %%Y')", "180 DAY"),
		"1Y": ("DATE_FORMAT(posting_date, '%%b %%Y')", "365 DAY"),
	}
	fmt, interval = period_map.get(period, period_map["1M"])

	sales_rows = frappe.db.sql(
		f"""
        SELECT {fmt} AS label, SUM(grand_total) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND is_return  = 0
          AND company    = %(company)s
          AND posting_date >= DATE_SUB(CURDATE(), INTERVAL {interval})
        GROUP BY label
        ORDER BY MIN(posting_date) ASC
        """,
		{"company": company},
		as_dict=True,
	)

	purchase_rows = frappe.db.sql(
		f"""
        SELECT {fmt} AS label, SUM(grand_total) AS amount
        FROM `tabPurchase Receipt`
        WHERE docstatus = 1
          AND is_return  = 0
          AND company    = %(company)s
          AND posting_date >= DATE_SUB(CURDATE(), INTERVAL {interval})
        GROUP BY label
        ORDER BY MIN(posting_date) ASC
        """,
		{"company": company},
		as_dict=True,
	)

	# Build label-aligned arrays
	all_labels = sorted(
		{r.label for r in sales_rows} | {r.label for r in purchase_rows},
		key=lambda lbl: lbl,
	)
	sales_map = {r.label: float(r.amount or 0) for r in sales_rows}
	purchase_map = {r.label: float(r.amount or 0) for r in purchase_rows}

	return surge_response(
		{
			"labels": all_labels,
			"sales": [sales_map.get(lbl, 0) for lbl in all_labels],
			"purchases": [purchase_map.get(lbl, 0) for lbl in all_labels],
		}
	)


@frappe.whitelist(allow_guest=False)
def manager_get_list(
	doctype: str,
	fields: str = "[]",
	filters: str = "[]",
	order_by: str = "modified desc",
	limit_start: int = 0,
	limit_page_length: int = 20,
) -> object:
	"""
	Frappe-permission-elevated list fetch for Manager/Supervisor dashboard pages.

	frappe.client.get_list applies record-level "if_owner" restrictions even when
	the role grants read access — a POS Manager who lacks 'Accounts Manager' role
	gets zero rows for Sales Invoice, PO, etc.  This endpoint re-checks Manager
	access at the POS-profile level (our auth boundary) then fetches with
	ignore_permissions=True so managers see all company records, same as built-in
	ERPNext manager reports.
	"""
	import json

	_require_manager()

	# Allowlist — never expose doctypes outside dashboard scope
	_ALLOWED = {
		"Item",
		"Item Group",
		"Brand",
		"Bin",
		"Purchase Order",
		"Purchase Receipt",
		"Sales Invoice",
		"Warehouse",
		"Customer",
		"Supplier",
		"POS Profile",
		"Item Reorder",
		"POS Opening Entry",
	}
	if doctype not in _ALLOWED:
		frappe.throw(f"DocType '{doctype}' is not accessible via this endpoint.", frappe.PermissionError)

	try:
		parsed_fields = json.loads(fields) if fields else []
		parsed_filters = json.loads(filters) if filters else []
	except Exception:
		frappe.throw("Invalid fields or filters JSON.", frappe.ValidationError)

	rows = frappe.get_list(
		doctype,
		fields=parsed_fields or ["name"],
		filters=parsed_filters,
		order_by=order_by,
		limit_start=int(limit_start),
		limit_page_length=int(limit_page_length),
		ignore_permissions=True,
	)
	return surge_response({"data": rows})


def _require_manager() -> None:
	if not frappe.db.exists(
		"POS Profile User",
		{
			"user": frappe.session.user,
			"access_level": ["in", ["Manager", "Supervisor"]],
			"status": "Active",
		},
	):
		frappe.throw("Not permitted.", frappe.PermissionError)


@frappe.whitelist(allow_guest=False)
def get_stock_inventory(search: str = "", page: int = 0, page_size: int = 25) -> object:
	"""Stock Inventory with item_name via SQL JOIN — frappe.client.get_list cannot JOIN."""
	offset = int(page) * int(page_size)
	like = f"%{search}%" if search else "%"
	rows = frappe.db.sql(
		"""
        SELECT b.item_code, i.item_name, b.warehouse,
               b.actual_qty, b.reserved_qty, b.ordered_qty
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code AND i.disabled = 0
        WHERE (b.item_code LIKE %(like)s OR i.item_name LIKE %(like)s)
        ORDER BY b.actual_qty ASC
        LIMIT %(page_size)s OFFSET %(offset)s
        """,
		{"like": like, "page_size": int(page_size), "offset": offset},
		as_dict=True,
	)
	return surge_response(
		[
			{
				"item_code": r.item_code,
				"item_name": r.item_name,
				"warehouse": r.warehouse,
				"actual_qty": float(r.actual_qty or 0),
				"reserved_qty": float(r.reserved_qty or 0),
				"ordered_qty": float(r.ordered_qty or 0),
			}
			for r in rows
		]
	)
