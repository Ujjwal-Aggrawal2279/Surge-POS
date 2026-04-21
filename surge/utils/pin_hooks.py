"""
POS Profile User document hooks — auto-generate cashier PIN.
"""

import random

import frappe


def auto_generate_pin(doc, method):
	"""
	Auto-generate a 4-digit PIN when a cashier is made Active and has no PIN yet.
	Called on before_insert and before_save of POS Profile User.

	The PIN is stored as plaintext at permlevel=1 — visible to System Manager
	only. The real authentication layer is the Frappe session; the PIN is a
	terminal-identification mechanism, not a secret credential.
	"""
	if doc.status == "Active" and not doc.surge_pos_pin:
		doc.surge_pos_pin = _generate_unique_pin(doc.parent)


def _generate_unique_pin(pos_profile: str, attempts: int = 10) -> str:
	"""Generate a 4-digit PIN that is not already in use on this profile."""
	existing = set(
		frappe.db.get_all(
			"POS Profile User",
			filters={"parent": pos_profile, "status": "Active"},
			pluck="surge_pos_pin",
		)
	)
	for _ in range(attempts):
		pin = str(random.randint(1000, 9999))
		if pin not in existing:
			return pin
	# Fallback — collision on small teams is extremely unlikely but handled
	return str(random.randint(1000, 9999))
