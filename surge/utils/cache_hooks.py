"""
Frappe doc_event hooks — bust Surge caches when ERPNext master data changes.
Called by Frappe after insert/update/trash on watched DocTypes.
"""

import frappe

from surge.utils import tombstone as tb
from surge.utils.cache import cache_key, invalidate


def _coalesced_publish(event: str, message: dict, gate_key: str, window_sec: int = 1) -> None:
	"""
	Publish a realtime event at most once per window_sec per gate_key.
	First call fires immediately; subsequent calls within the window are suppressed.
	Uses Redis SETNX so it works correctly across all gunicorn workers.
	"""
	redis_key = f"surge:rt_gate:{gate_key}"
	# set_value with expires_in_sec only sets if key doesn't exist when using nx=True
	cache = frappe.cache()
	# frappe's cache().set_value doesn't expose NX — use execute_command directly
	acquired = cache.execute_command("SET", cache.make_key(redis_key), 1, "EX", window_sec, "NX")
	if acquired:
		frappe.publish_realtime(  # nosemgrep: frappe-realtime-pick-room — intentional site-wide cache-invalidation broadcast
			event, message, after_commit=True
		)


def _invalidate_all_item_caches() -> None:
	profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, pluck="name")
	for profile in profiles:
		invalidate(cache_key("items", profile))
		invalidate(cache_key("prices", profile))


def on_item_update(doc, method=None):
	"""Item changed — invalidate caches; tombstone if disabled."""
	_invalidate_all_item_caches()
	if doc.disabled:
		tb.add(doc.name)
	_coalesced_publish("surge:invalidate", {"type": "items"}, gate_key="items")


def on_item_trash(doc, method=None):
	"""Item deleted — tombstone it and push realtime invalidation."""
	tb.add(doc.name)
	_invalidate_all_item_caches()
	_coalesced_publish("surge:invalidate", {"type": "items"}, gate_key="items")


def on_customer_update(doc, method=None):
	invalidate(cache_key("customers", frappe.local.site))


def on_bin_update(doc, method=None):
	"""Bin.on_update — kept as fallback for direct bin saves."""
	if doc.warehouse:
		invalidate(cache_key("stock", doc.warehouse))


def on_sle_submit(doc, method=None):
	"""Stock Ledger Entry submitted — always fires regardless of Bin update path."""
	warehouse = doc.warehouse or ""
	if warehouse:
		invalidate(cache_key("stock", warehouse))
	# Gate key is per-warehouse so events for different warehouses are independent
	_coalesced_publish(
		"surge:invalidate",
		{"type": "stock", "warehouse": warehouse},
		gate_key=f"stock:{warehouse}",
	)


def on_item_price_update(doc, method=None):
	"""Price changed — invalidate price cache for affected POS profiles."""
	if not doc.price_list:
		return
	profiles = frappe.db.sql(
		"""
        SELECT name FROM `tabPOS Profile`
        WHERE selling_price_list = %s AND disabled = 0
        """,
		(doc.price_list,),
		pluck="name",
	)
	for profile in profiles:
		invalidate(cache_key("prices", profile))
	_coalesced_publish("surge:invalidate", {"type": "items"}, gate_key="items")
