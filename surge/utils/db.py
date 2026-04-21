from typing import Any

import frappe


def raw_query(sql: str, values: tuple = ()) -> list[tuple]:
	return frappe.db.sql(sql, values)


def raw_query_dict(sql: str, values: tuple = ()) -> list[dict]:
	return frappe.db.sql(sql, values, as_dict=True)


def items_query(since: str = "", limit: int = 500) -> list[dict]:
	params: dict[str, Any] = {"limit": limit}
	since_clause = ""
	if since:
		since_clause = "AND i.modified > %(since)s"
		params["since"] = since

	sql = f"""
        SELECT
            i.name          AS item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            i.has_variants,
            i.image,
            i.modified,
            GROUP_CONCAT(ib.barcode SEPARATOR ',') AS barcodes
        FROM `tabItem` i
        LEFT JOIN `tabItem Barcode` ib ON ib.parent = i.name
        WHERE i.disabled = 0
          AND i.is_sales_item = 1
          {since_clause}
        GROUP BY i.name
        ORDER BY i.modified ASC
        LIMIT %(limit)s
    """

	return frappe.db.sql(sql, params, as_dict=True)


def stock_query(warehouse: str, since: str = "") -> list[dict]:
	if since:
		return frappe.db.sql(
			"""
            SELECT item_code, warehouse, actual_qty, reserved_qty, modified
            FROM `tabBin`
            WHERE warehouse = %(warehouse)s
              AND modified > %(since)s
            ORDER BY modified ASC
            LIMIT 10000
            """,
			{"warehouse": warehouse, "since": since},
			as_dict=True,
		)
	return frappe.db.sql(
		"""
        SELECT item_code, warehouse, actual_qty, reserved_qty, modified
        FROM `tabBin`
        WHERE warehouse = %(warehouse)s
          AND actual_qty > 0
        ORDER BY modified ASC
        LIMIT 10000
        """,
		{"warehouse": warehouse},
		as_dict=True,
	)


def customers_query(since: str = "", limit: int = 1000) -> list[dict]:
	params: dict[str, Any] = {"limit": limit}
	since_clause = ""
	if since:
		since_clause = "AND modified > %(since)s"
		params["since"] = since

	sql = f"""
        SELECT
            name        AS customer_id,
            customer_name,
            mobile_no,
            email_id,
            tax_id      AS gstin,
            customer_group,
            modified
        FROM `tabCustomer`
        WHERE disabled = 0
          {since_clause}
        ORDER BY modified ASC
        LIMIT %(limit)s
    """

	return frappe.db.sql(sql, params, as_dict=True)
