import frappe
from surge.utils.cache import get_or_compute, cache_key, STOCK_CACHE_TTL
from surge.utils.json import surge_response
from surge.utils.db import stock_query
from surge.utils.permissions import require_warehouse_access


@frappe.whitelist(allow_guest=False)
def get_stock(warehouse: str, since: str = ""):
    require_warehouse_access(warehouse)

    if since:
        stock = stock_query(warehouse=warehouse, since=since)
        watermark = str(max(s["modified"] for s in stock)) if stock else None
        return surge_response({"stock": stock, "watermark": watermark, "count": len(stock)})

    key = cache_key("stock", warehouse)

    def _compute():
        rows = stock_query(warehouse=warehouse, since="")
        wm = str(max(r["modified"] for r in rows)) if rows else None
        return {"stock": rows, "watermark": wm, "count": len(rows)}

    result = get_or_compute(key, _compute, STOCK_CACHE_TTL)
    return surge_response(result)
