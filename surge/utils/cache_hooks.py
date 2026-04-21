"""
Frappe doc_event hooks — bust Surge caches when ERPNext master data changes.
Called by Frappe after insert/update on watched DocTypes.
"""
import frappe
from surge.utils.cache import invalidate, cache_key


def on_item_update(doc, method=None):
    """Item changed — invalidate item cache for all POS profiles."""
    profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, pluck="name")
    for profile in profiles:
        invalidate(cache_key("items", profile))
        invalidate(cache_key("prices", profile))


def on_customer_update(doc, method=None):
    invalidate(cache_key("customers", frappe.local.site))


def on_bin_update(doc, method=None):
    """Stock bin changed — invalidate stock cache for that warehouse."""
    if doc.warehouse:
        invalidate(cache_key("stock", doc.warehouse))


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
