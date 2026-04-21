from collections.abc import Callable
from threading import Lock
from typing import Any

import frappe
from cachetools import TTLCache

from .json import dumps, loads

_l1: TTLCache = TTLCache(maxsize=200, ttl=30)
_l1_lock = Lock()
_computing: set[str] = set()
_computing_lock = Lock()

ITEM_CACHE_TTL = 300
STOCK_CACHE_TTL = 60
CUSTOMER_CACHE_TTL = 300


def cache_key(namespace: str, *parts: str) -> str:
	return "surge:" + namespace + ":" + ":".join(parts)


def _l1_get(key: str) -> Any:
	with _l1_lock:
		return _l1.get(key)


def _l1_set(key: str, data: Any) -> None:
	with _l1_lock:
		_l1[key] = data


def _l1_delete(key: str) -> None:
	with _l1_lock:
		_l1.pop(key, None)


def get_cached(key: str) -> Any:
	val = _l1_get(key)
	if val is not None:
		return val
	raw = frappe.cache().get_value(key)
	if raw is not None:
		data = loads(raw)
		_l1_set(key, data)
		return data
	return None


def set_cached(key: str, data: Any, ttl: int) -> None:
	_l1_set(key, data)
	frappe.cache().set_value(key, dumps(data), expires_in_sec=ttl)


def get_or_compute(key: str, fn: Callable[[], Any], ttl: int) -> Any:
	val = _l1_get(key)
	if val is not None:
		return val

	raw = frappe.cache().get_value(key)
	if raw is not None:
		data = loads(raw)
		_l1_set(key, data)
		return data

	with _computing_lock:
		already_computing = key in _computing
		if not already_computing:
			_computing.add(key)

	try:
		if already_computing:
			raw = frappe.cache().get_value(key)
			if raw is not None:
				data = loads(raw)
				_l1_set(key, data)
				return data

		data = fn()
		set_cached(key, data, ttl)
		return data
	finally:
		if not already_computing:
			with _computing_lock:
				_computing.discard(key)


def invalidate(key: str) -> None:
	_l1_delete(key)
	frappe.cache().delete_value(key)


def invalidate_items(profile: str) -> None:
	invalidate(cache_key("items", profile))
	invalidate(cache_key("prices", profile))


def invalidate_stock(warehouse: str) -> None:
	invalidate(cache_key("stock", warehouse))


def invalidate_customers() -> None:
	invalidate(cache_key("customers", frappe.local.site))
