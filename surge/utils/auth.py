"""
Surge POS auth hooks and session helpers.

on_session_creation:
  Fires after every successful Frappe login.
  Redirects POS-only users to /surge instead of the desk.
  Must NEVER raise — a crash here blocks the entire login.

get_session_user_flags:
  Returns pos_access / desk_access flags for the current user.
  Used by surge.py to populate SURGE_CONFIG.
"""
import frappe


# ---------------------------------------------------------------------------
# Session hook — registered in hooks.py
# ---------------------------------------------------------------------------

def on_session_creation(login_manager) -> None:
    """
    Called by Frappe after every successful login.

    Decision matrix:
      pos_access=1, desk_access=0 → redirect home_page to /surge
      pos_access=1, desk_access=1 → no redirect (desk lands, apps switcher available)
      pos_access=0, *             → no redirect (normal Frappe behaviour)

    Entry-point intent:
      If user logged in via /surge-login, the redirect is handled by that page's
      JS directly — this hook only fires for /login (default Frappe login).

    Worst cases:
      - Role table missing pos_access column (custom field not migrated yet)
        → IFNULL(pos_access, 0) returns 0 → no redirect → safe degradation
      - frappe.get_roles() returns empty list → return early
      - Any exception → log + return, NEVER propagate (would break login)
    """
    try:
        user = login_manager.user
        if user in ("Administrator", "Guest"):
            return

        roles = frappe.get_roles(user)
        if not roles:
            return

        row = frappe.db.sql(
            """
            SELECT
                MAX(desk_access)              AS has_desk,
                MAX(IFNULL(pos_access, 0))    AS has_pos
            FROM `tabRole`
            WHERE name IN %(roles)s
            """,
            {"roles": roles},
            as_dict=True,
        )

        if not row:
            return

        has_desk = bool(row[0].get("has_desk"))
        has_pos  = bool(row[0].get("has_pos"))

        if has_pos and not has_desk:
            frappe.local.response["home_page"] = "/surge"

    except Exception:
        # Log silently — never block login
        frappe.log_error(title="Surge: on_session_creation failed")


# ---------------------------------------------------------------------------
# Helper used by surge.py and surge-login.py
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def get_session_user_flags() -> dict:
    """Expose pos/desk flags for the current session — used by login_inject.js."""
    return get_user_pos_flags(frappe.session.user)


def get_user_pos_flags(user: str) -> dict:
    """
    Return pos_access and desk_access flags for a given user.
    Safe to call even if pos_access custom field is not yet migrated
    (IFNULL handles missing column gracefully at query level via exception catch).
    """
    if user in ("Guest",):
        return {"has_pos": False, "has_desk": False}

    if user == "Administrator":
        return {"has_pos": True, "has_desk": True}

    roles = frappe.get_roles(user)
    if not roles:
        return {"has_pos": False, "has_desk": False}

    try:
        row = frappe.db.sql(
            """
            SELECT
                MAX(desk_access)              AS has_desk,
                MAX(IFNULL(pos_access, 0))    AS has_pos
            FROM `tabRole`
            WHERE name IN %(roles)s
            """,
            {"roles": roles},
            as_dict=True,
        )
        if not row:
            return {"has_pos": False, "has_desk": False}

        return {
            "has_pos":  bool(row[0].get("has_pos")),
            "has_desk": bool(row[0].get("has_desk")),
        }

    except Exception:
        frappe.log_error(title="Surge: get_user_pos_flags failed")
        return {"has_pos": False, "has_desk": False}
