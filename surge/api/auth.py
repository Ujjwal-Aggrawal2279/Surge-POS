import hashlib
import frappe
from frappe.utils import now_datetime, add_to_date
from surge.utils.permissions import require_pos_profile_access
from surge.utils.json import surge_response

PIN_MAX_ATTEMPTS = 3
PIN_LOCKOUT_SECONDS = 300

_LOCKOUT_KEY  = "surge:pin_locked:{user}:{profile}"
_ATTEMPTS_KEY = "surge:pin_attempts:{user}:{profile}"


@frappe.whitelist(allow_guest=False)
def get_cashiers(pos_profile: str) -> object:
    require_pos_profile_access(pos_profile)

    rows = frappe.db.sql(
        """
        SELECT
            pu.user,
            u.full_name,
            u.user_image,
            pu.access_level,
            CASE WHEN pu.surge_pos_pin IS NOT NULL
                      AND pu.surge_pos_pin != ''
                 THEN 1 ELSE 0 END AS has_pin
        FROM `tabPOS Profile User` pu
        JOIN `tabUser` u ON u.name = pu.user
        WHERE pu.parent  = %(profile)s
          AND pu.status  = 'Active'
          AND u.enabled  = 1
        ORDER BY u.full_name ASC
        """,
        {"profile": pos_profile},
        as_dict=True,
    )

    for row in rows:
        row["locked"]        = _is_locked(row["user"], pos_profile)
        row["lockout_until"] = _lockout_until(row["user"], pos_profile)

    return surge_response({"cashiers": rows})


@frappe.whitelist(allow_guest=False)
def verify_pin(pos_profile: str, user: str, pin: str) -> object:
    require_pos_profile_access(pos_profile)

    pin = (pin or "").strip()
    if len(pin) != 64 or not all(c in "0123456789abcdef" for c in pin):
        return surge_response({"status": "invalid", "message": "Invalid PIN format."})

    if _is_locked(user, pos_profile):
        return surge_response({
            "status": "locked",
            "lockout_until": _lockout_until(user, pos_profile),
        })

    row = frappe.db.get_value(
        "POS Profile User",
        {"parent": pos_profile, "user": user, "status": "Active"},
        ["name", "access_level", "surge_pos_pin"],
        as_dict=True,
    )
    if not row:
        return surge_response({"status": "invalid", "message": "User not active on this profile."})

    if not frappe.db.get_value("User", user, "enabled"):
        return surge_response({"status": "invalid", "message": "User account is disabled."})

    if not row.surge_pos_pin:
        return surge_response({"status": "no_pin"})

    if pin != _hash_pin(row.surge_pos_pin):
        attempts = _increment_attempts(user, pos_profile)
        remaining = PIN_MAX_ATTEMPTS - attempts
        if remaining <= 0:
            _set_lockout(user, pos_profile)
            return surge_response({
                "status": "locked",
                "lockout_until": _lockout_until(user, pos_profile),
            })
        return surge_response({"status": "wrong_pin", "attempts_left": remaining})

    _clear_attempts(user, pos_profile)
    full_name = frappe.db.get_value("User", user, "full_name")
    _log_action("cashier_login", user=user, profile=pos_profile)

    return surge_response({
        "status": "ok",
        "user": user,
        "full_name": full_name,
        "access_level": row.access_level or "Cashier",
    })


@frappe.whitelist(allow_guest=False)
def set_pin(user: str, pin: str, pos_profile: str) -> object:
    require_pos_profile_access(pos_profile)
    _require_manager_on_profile(pos_profile)

    pin = (pin or "").strip()
    if not pin.isdigit() or not (4 <= len(pin) <= 8):
        frappe.throw("PIN must be 4–8 numeric digits.", frappe.ValidationError)

    row_name = frappe.db.get_value(
        "POS Profile User",
        {"parent": pos_profile, "user": user, "status": "Active"},
        "name",
    )
    if not row_name:
        frappe.throw(
            f"User {user!r} is not active on profile {pos_profile!r}.",
            frappe.ValidationError,
        )

    frappe.db.set_value("POS Profile User", row_name, "surge_pos_pin", pin)
    frappe.db.commit()

    _log_action("pin_set", user=user, profile=pos_profile, by=frappe.session.user)
    return surge_response({"status": "ok"})


@frappe.whitelist(allow_guest=False)
def override_lockout(
    locked_user: str,
    supervisor_pin: str,
    pos_profile: str,
) -> object:
    require_pos_profile_access(pos_profile)

    supervisor = frappe.session.user

    result = frappe.parse_json(
        verify_pin(pos_profile=pos_profile, user=supervisor, pin=supervisor_pin).data
    )
    if result.get("status") != "ok":
        return surge_response(result)

    access = frappe.db.get_value(
        "POS Profile User",
        {"parent": pos_profile, "user": supervisor},
        "access_level",
    ) or "Cashier"

    if access not in ("Supervisor", "Manager"):
        return surge_response({
            "status": "forbidden",
            "message": "Only Supervisors and Managers can override lockouts.",
        })

    _clear_attempts(locked_user, pos_profile)
    _clear_lockout(locked_user, pos_profile)

    _log_action("lockout_override", user=locked_user, profile=pos_profile, by=supervisor)

    return surge_response({"status": "ok", "message": f"Lockout cleared for {locked_user}."})


@frappe.whitelist(allow_guest=False)
def forgot_pin(user: str, pos_profile: str) -> object:
    require_pos_profile_access(pos_profile)

    if not frappe.db.exists(
        "POS Profile User",
        {"parent": pos_profile, "user": user, "status": "Active"},
    ):
        return surge_response({"status": "error", "message": "User not active on this profile."})

    cashier_name = frappe.db.get_value("User", user, "full_name")
    if not cashier_name:
        return surge_response({"status": "error", "message": "User not found."})

    try:
        frappe.sendmail(
            recipients=[user],
            subject="Surge POS — PIN Reset Requested",
            message=f"""
                <p>Hi {cashier_name},</p>
                <p>A PIN reset was requested for your cashier account on
                   POS Profile <strong>{pos_profile}</strong>.</p>
                <p>Please contact your manager — they will set a new PIN
                   for you from the Surge POS settings.</p>
                <p>If you did not request this, inform your manager immediately.</p>
                <p>— Surge POS</p>
            """,
            now=True,
        )
    except Exception:
        frappe.logger().warning(
            f"Surge: forgot_pin email failed for {user}"
        )

    managers = frappe.db.get_all(
        "POS Profile User",
        filters={"parent": pos_profile, "access_level": "Manager", "status": "Active"},
        pluck="user",
    )
    notify_users = list({*managers, "Administrator"})

    for notify_user in notify_users:
        if notify_user == user:
            continue
        if not frappe.db.exists("User", {"name": notify_user, "enabled": 1}):
            continue
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"PIN Reset Request — {cashier_name}",
                "email_content": (
                    f"Cashier <b>{cashier_name}</b> has requested a PIN reset "
                    f"on POS Profile <b>{pos_profile}</b>. "
                    f"Please set their PIN from Surge POS Settings."
                ),
                "for_user": notify_user,
                "type": "Alert",
                "from_user": frappe.session.user,
                "document_type": "POS Profile",
                "document_name": pos_profile,
            }).insert(ignore_permissions=True)
        except Exception:
            frappe.logger().warning(f"Surge: could not create notification for {notify_user}")

    frappe.db.commit()
    _log_action("forgot_pin", user=user, profile=pos_profile)

    return surge_response({"status": "ok"})


@frappe.whitelist(allow_guest=False)
def logout_cashier(pos_profile: str, user: str) -> object:
    require_pos_profile_access(pos_profile)
    _log_action("cashier_logout", user=user, profile=pos_profile)
    return surge_response({"status": "ok"})


def _lockout_key(user: str, profile: str) -> str:
    return _LOCKOUT_KEY.format(user=user, profile=profile)


def _attempts_key(user: str, profile: str) -> str:
    return _ATTEMPTS_KEY.format(user=user, profile=profile)


def _is_locked(user: str, profile: str) -> bool:
    try:
        return bool(frappe.cache().get_value(_lockout_key(user, profile)))
    except Exception:
        frappe.logger().warning(f"Surge: Redis unavailable — lockout check skipped for {user}@{profile}")
        return False


def _lockout_until(user: str, profile: str) -> str | None:
    try:
        val = frappe.cache().get_value(_lockout_key(user, profile))
        return val if val else None
    except Exception:
        return None


def _set_lockout(user: str, profile: str) -> None:
    until = add_to_date(now_datetime(), seconds=PIN_LOCKOUT_SECONDS)
    try:
        frappe.cache().set_value(
            _lockout_key(user, profile),
            until.isoformat(),
            expires_in_sec=PIN_LOCKOUT_SECONDS,
        )
        frappe.cache().delete_value(_attempts_key(user, profile))
    except Exception:
        frappe.logger().warning(f"Surge: Redis unavailable — lockout set skipped for {user}@{profile}")


def _clear_lockout(user: str, profile: str) -> None:
    try:
        frappe.cache().delete_value(_lockout_key(user, profile))
    except Exception:
        pass


def _increment_attempts(user: str, profile: str) -> int:
    try:
        key = _attempts_key(user, profile)
        count = int(frappe.cache().get_value(key) or 0) + 1
        frappe.cache().set_value(key, count, expires_in_sec=PIN_LOCKOUT_SECONDS * 2)
        return count
    except Exception:
        frappe.logger().warning(f"Surge: Redis unavailable — attempt increment skipped for {user}@{profile}")
        return 1


def _clear_attempts(user: str, profile: str) -> None:
    try:
        frappe.cache().delete_value(_attempts_key(user, profile))
    except Exception:
        pass


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def _require_manager_on_profile(pos_profile: str) -> None:
    user = frappe.session.user
    if user == "Administrator":
        return

    access = frappe.db.get_value(
        "POS Profile User",
        {"parent": pos_profile, "user": user},
        "access_level",
    )
    if access not in ("Manager",):
        frappe.throw("Only Managers can set cashier PINs.", frappe.PermissionError)


def _log_action(action: str, user: str, profile: str, by: str | None = None) -> None:
    try:
        frappe.logger().info(
            f"Surge audit | action={action} user={user} profile={profile} "
            f"by={by or user} terminal={frappe.session.user}"
        )
    except Exception:
        pass
