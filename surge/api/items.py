import time

import frappe

from surge.utils.cache import ITEM_CACHE_TTL, cache_key, get_or_compute
from surge.utils.db import items_query
from surge.utils.json import surge_response
from surge.utils.permissions import require_pos_profile_access, require_pos_role
from surge.utils import tombstone as tb


@frappe.whitelist(allow_guest=False)
def get_pos_profiles():
	require_pos_role()
	user = frappe.session.user

	rows = frappe.db.sql(
		"""
        SELECT p.name, p.warehouse, p.currency, p.selling_price_list,
               p.company,
               p.allow_discount_change,
               p.allow_rate_change,
               IFNULL(p.discount_limit_cashier, 5)    AS discount_limit_cashier,
               IFNULL(p.discount_limit_supervisor, 15) AS discount_limit_supervisor,
               IFNULL(p.discount_limit_manager, 100)   AS discount_limit_manager
        FROM `tabPOS Profile` p
        WHERE p.disabled = 0
          AND (
              NOT EXISTS (
                  SELECT 1 FROM `tabPOS Profile User` pu WHERE pu.parent = p.name
              )
              OR EXISTS (
                  SELECT 1 FROM `tabPOS Profile User` pu
                  WHERE pu.parent = p.name AND pu.user = %(user)s
              )
              OR %(user)s = 'Administrator'
          )
        ORDER BY p.name ASC
        """,
		{"user": user},
		as_dict=True,
	)

	# Attach payment modes from child table for each profile
	for profile in rows:
		modes = frappe.db.get_all(
			"POS Payment Method",
			filters={"parent": profile["name"]},
			fields=["mode_of_payment"],
			order_by="idx asc",
		)
		profile["payment_modes"] = [m["mode_of_payment"] for m in modes] or ["Cash"]

	return surge_response({"profiles": rows})


@frappe.whitelist(allow_guest=False)
def get_items(profile: str, since: str = "", limit: int = 500):
	require_pos_profile_access(profile)
	limit = min(int(limit), 2000)

	if since:
		items = _fetch_and_annotate(since=since, limit=limit)
		watermark = str(max(i["modified"] for i in items)) if items else None
		# Include tombstones so clients can remove deleted/disabled items from local cache
		try:
			since_ts = frappe.utils.get_datetime(since).timestamp()
		except Exception:
			since_ts = time.time() - 86_400
		dead = tb.since(since_ts)
		return surge_response({"items": items, "watermark": watermark, "count": len(items), "tombstones": dead})

	key = cache_key("items", profile)

	def _compute():
		rows = _fetch_and_annotate(since="", limit=limit)
		wm = str(max(r["modified"] for r in rows)) if rows else None
		return {"items": rows, "watermark": wm, "count": len(rows)}

	result = get_or_compute(key, _compute, ITEM_CACHE_TTL)
	return surge_response(result)


@frappe.whitelist(allow_guest=False)
def get_item_prices(profile: str, since: str = "", limit: int = 2000):
	require_pos_profile_access(profile)

	pos_profile = frappe.get_cached_doc("POS Profile", profile)
	price_list = pos_profile.selling_price_list or "Standard Selling"
	limit = min(int(limit), 5000)

	if since:
		prices = _fetch_prices(price_list=price_list, since=since, limit=limit)
		watermark = str(max(p["modified"] for p in prices)) if prices else None
		return surge_response(
			{
				"prices": prices,
				"price_list": price_list,
				"watermark": watermark,
				"count": len(prices),
			}
		)

	key = cache_key("prices", profile)

	def _compute():
		rows = _fetch_prices(price_list=price_list, since="", limit=limit)
		wm = str(max(r["modified"] for r in rows)) if rows else None
		return {"prices": rows, "price_list": price_list, "watermark": wm, "count": len(rows)}

	result = get_or_compute(key, _compute, ITEM_CACHE_TTL)
	return surge_response(result)


def _fetch_and_annotate(since: str, limit: int) -> list[dict]:
	items = items_query(since=since, limit=limit)
	for item in items:
		raw = item.get("barcodes") or ""
		item["barcodes"] = [b for b in raw.split(",") if b]
	return items


def _fetch_prices(price_list: str, since: str, limit: int) -> list[dict]:
	params: dict = {"price_list": price_list, "limit": limit}
	since_clause = ""
	if since:
		since_clause = "AND modified > %(since)s"
		params["since"] = since

	sql = f"""
        SELECT item_code, price_list_rate, currency, price_list, modified
        FROM `tabItem Price`
        WHERE price_list = %(price_list)s
          AND selling = 1
          {since_clause}
        ORDER BY modified ASC
        LIMIT %(limit)s
    """

	return frappe.db.sql(sql, params, as_dict=True)
