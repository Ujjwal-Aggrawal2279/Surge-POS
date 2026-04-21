"""
Patch: create Surge POS custom fields on existing installations.
Idempotent — create_custom_fields(update=True) is safe to re-run.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from surge.setup.custom_fields import SURGE_CUSTOM_FIELDS


def execute():
	create_custom_fields(SURGE_CUSTOM_FIELDS, update=True)
	frappe.db.commit()
