import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from surge.setup.custom_fields import SURGE_CUSTOM_FIELDS


def after_install():
	create_custom_fields(SURGE_CUSTOM_FIELDS, update=True)
	_setup_pos_profile_perms()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — custom fields must be committed before site setup continues


def _setup_pos_profile_perms():
	# Any Custom DocPerm entry causes all default tabDocPerm rows to be ignored —
	# replicate every default POS Profile perm before adding our permlevel=1 row.
	_ensure_perm("Accounts Manager", 0, read=1, write=1, create=1, delete=1, report=1)
	_ensure_perm("Accounts User", 0, read=1, report=1)
	_ensure_perm("System Manager", 0, read=1, write=1, create=1, delete=1, report=1)
	_ensure_perm("System Manager", 1, read=1, write=1)


def _ensure_perm(role: str, permlevel: int, **flags) -> None:
	if frappe.db.exists(
		"Custom DocPerm",
		{"parent": "POS Profile", "role": role, "permlevel": permlevel},
	):
		return

	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": "POS Profile",
			"role": role,
			"permlevel": permlevel,
			**flags,
		}
	).insert(ignore_permissions=True)
