"""
Surge before_uninstall hook — removes all custom fields added by this app.
Runs before Frappe drops the app from the site.
"""
import frappe
from surge.setup.custom_fields import SURGE_CUSTOM_FIELDS


def before_uninstall():
    for doctype, fields in SURGE_CUSTOM_FIELDS.items():
        for field in fields:
            name = f"{doctype}-{field['fieldname']}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, ignore_permissions=True)

    frappe.db.commit()
