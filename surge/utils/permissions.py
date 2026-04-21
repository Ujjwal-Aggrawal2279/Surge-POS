"""
Permission guards for Surge POS API endpoints.
Check access at the API boundary — direct SQL is safe once these pass.
"""
import frappe


POS_ROLES = {"POS User", "System Manager", "Administrator"}


def require_pos_role() -> None:
    """User must have at least one POS role."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.AuthenticationError)
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not user_roles & POS_ROLES:
        frappe.throw(
            "You do not have permission to access Surge POS",
            frappe.PermissionError,
        )


def require_pos_profile_access(profile: str) -> None:
    """
    User must have POS role AND be listed in the POS Profile's
    applicable users (or the profile has no user restrictions).
    """
    require_pos_role()

    if frappe.session.user in ("Administrator",):
        return

    # Check if profile restricts access to specific users
    allowed_users = frappe.db.sql(
        """
        SELECT u.user
        FROM `tabPOS Profile User` u
        WHERE u.parent = %s AND u.default = 1
        """,
        (profile,),
        as_list=True,
    )

    # If no users listed → open to all POS role holders
    if not allowed_users:
        return

    flat = [row[0] for row in allowed_users]
    if frappe.session.user not in flat:
        frappe.throw(
            f"You do not have access to POS Profile '{profile}'",
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
                  WHERE pu.parent = p.name AND pu.user = %(user)s
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
