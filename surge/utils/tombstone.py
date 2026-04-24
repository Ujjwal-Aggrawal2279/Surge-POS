"""
Redis ZSET tombstone store for deleted/disabled items.
Score = unix timestamp, member = item_code.
Lets delta-sync clients know which items to remove from their local cache.
"""

import time

import frappe

_KEY = "surge:tombstones"
_TTL = 86_400  # 24 hours — enough for any offline client to reconnect and catch up


def add(item_code: str) -> None:
    ts = time.time()
    cache = frappe.cache()
    cache.zadd(_KEY, {item_code: ts})
    # Prune entries older than TTL to keep the set bounded
    cache.zremrangebyscore(_KEY, "-inf", ts - _TTL)


def since(since_ts: float) -> list[str]:
    """Return item codes tombstoned after since_ts (unix timestamp)."""
    try:
        members = frappe.cache().zrangebyscore(_KEY, since_ts, "+inf")
        if not members:
            return []
        # frappe.cache() may return bytes
        return [m.decode() if isinstance(m, bytes) else m for m in members]
    except Exception:
        return []
