"""
POS Profile hooks — auto-generate cashier PINs when users are added.
"""

import random

import frappe


def auto_generate_pins_for_profile(doc, method=None):
	"""
	Called before_save on POS Profile.
	Assigns a unique 4-digit PIN to any Active user row that has none.
	Iterating the parent's child table is the reliable pattern — child-doc
	hooks are called before Frappe serialises the row, so assignments made
	there are silently discarded.
	"""
	assigned: set[str] = {row.surge_pos_pin for row in doc.applicable_for_users if row.surge_pos_pin}
	for row in doc.applicable_for_users:
		if row.status == "Active" and not row.surge_pos_pin:
			row.surge_pos_pin = _unique_pin(assigned)
			assigned.add(row.surge_pos_pin)


def _unique_pin(existing: set[str], attempts: int = 20) -> str:
	for _ in range(attempts):
		pin = str(random.randint(1000, 9999))
		if pin not in existing:
			return pin
	return str(random.randint(1000, 9999))
