"""
Permission guards for Surge POS API endpoints.
Check access at the API boundary — direct SQL is safe once these pass.
"""

import frappe

POS_ROLES = {"POS User", "System Manager", "Administrator"}
MANAGER_ROLES = {"System Manager", "Administrator"}


def require_pos_role() -> None:
	"""User must have at least one POS role."""
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Not permitted"), frappe.AuthenticationError)
	user_roles = set(frappe.get_roles(frappe.session.user))
	if not user_roles & POS_ROLES:
		frappe.throw(
			frappe._("You do not have permission to access Surge POS"),
			frappe.PermissionError,
		)


def require_pos_profile_access(profile: str) -> None:
	"""
	User must have POS role AND be Active on the POS Profile (if it has user restrictions).
	Profiles with zero users listed are open to all POS role holders.
	"""
	require_pos_role()

	if frappe.session.user in ("Administrator",):
		return

	if frappe.db.get_value("POS Profile", profile, "disabled"):
		frappe.throw(f"POS Profile '{profile}' is disabled.", frappe.PermissionError)

	# First: does this profile restrict access to specific users at all?
	has_any_users = frappe.db.count("POS Profile User", {"parent": profile})
	if not has_any_users:
		return  # Open profile — all POS role holders allowed

	# Profile has user restrictions — caller must be Active
	is_active = frappe.db.exists(
		"POS Profile User",
		{"parent": profile, "user": frappe.session.user, "status": "Active"},
	)
	if not is_active:
		frappe.throw(
			f"You do not have access to POS Profile '{profile}'",
			frappe.PermissionError,
		)


def require_manager_role() -> None:
	"""User must be System Manager or Administrator to perform privileged operations."""
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Not permitted"), frappe.AuthenticationError)
	user_roles = set(frappe.get_roles(frappe.session.user))
	if not user_roles & MANAGER_ROLES:
		frappe.throw(
			frappe._("This action requires Manager access"),
			frappe.PermissionError,
		)


def require_surge_manager_role() -> None:
	"""User must have Manager access level on at least one active POS Profile.
	Use this instead of require_manager_role() for Surge POS operations — Surge
	Managers are defined in POS Profile User, not in Frappe system roles."""
	require_pos_role()
	if frappe.session.user in ("Administrator",):
		return
	user_roles = set(frappe.get_roles(frappe.session.user))
	if "System Manager" in user_roles:
		return  # System Manager has full access to all Surge manager operations
	is_manager = frappe.db.exists(
		"POS Profile User",
		{"user": frappe.session.user, "access_level": "Manager", "status": "Active"},
	)
	if not is_manager:
		frappe.throw(
			frappe._("This action requires Surge Manager access"),
			frappe.PermissionError,
		)


def require_warehouse_access(warehouse: str) -> None:
	"""
	Warehouse must be linked to an active POS Profile the current user can access.
	Prevents one cashier from reading another terminal's warehouse stock.
	"""
	require_pos_role()

	if frappe.session.user in ("Administrator",):
		return

	# Find active profiles linked to this warehouse that the user can access
	# A profile is accessible if: it has no user restrictions, OR the user is listed
	profiles = frappe.db.sql(
		"""
        SELECT p.name
        FROM `tabPOS Profile` p
        WHERE p.warehouse = %(warehouse)s
          AND p.disabled = 0
          AND (
              NOT EXISTS (
                  SELECT 1 FROM `tabPOS Profile User` pu WHERE pu.parent = p.name
              )
              OR EXISTS (
                  SELECT 1 FROM `tabPOS Profile User` pu
                  WHERE pu.parent = p.name AND pu.user = %(user)s AND pu.status = 'Active'
              )
          )
        LIMIT 1
        """,
		{"warehouse": warehouse, "user": frappe.session.user},
	)
	if not profiles:
		frappe.throw(
			f"You do not have access to warehouse '{warehouse}'",
			frappe.PermissionError,
		)
