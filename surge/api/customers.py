import frappe

from surge.utils.cache import CUSTOMER_CACHE_TTL, cache_key, get_or_compute
from surge.utils.db import customers_query
from surge.utils.json import surge_response
from surge.utils.permissions import require_pos_role


@frappe.whitelist(allow_guest=False)
def get_customers(since: str = "", limit: int = 1000):
	require_pos_role()
	limit = min(int(limit), 5000)

	if since:
		customers = customers_query(since=since, limit=limit)
		watermark = str(max(c["modified"] for c in customers)) if customers else None
		return surge_response({"customers": customers, "watermark": watermark, "count": len(customers)})

	key = cache_key("customers", frappe.local.site)

	def _compute():
		rows = customers_query(since="", limit=limit)
		wm = str(max(r["modified"] for r in rows)) if rows else None
		return {"customers": rows, "watermark": wm, "count": len(rows)}

	result = get_or_compute(key, _compute, CUSTOMER_CACHE_TTL)
	return surge_response(result)
