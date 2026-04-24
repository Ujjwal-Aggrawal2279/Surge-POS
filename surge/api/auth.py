import base64
import hashlib
import hmac
import json
import uuid as _uuid

import frappe
from frappe.utils import add_to_date, now_datetime

from surge.utils.json import surge_response
from surge.utils.permissions import require_pos_profile_access

PIN_MAX_ATTEMPTS = 3
PIN_LOCKOUT_SECONDS = 300
APPROVAL_TOKEN_TTL = 1800  # 30 minutes — request outlives cashier's 3-min display timer

_LOCKOUT_KEY = "surge:pin_locked:{user}:{profile}"
_ATTEMPTS_KEY = "surge:pin_attempts:{user}:{profile}"
_TOKEN_KEY = "surge:approval_token:{token_hash}"
_APPROVAL_REQ_KEY = "surge:approval_req:{req_id}"
_APPROVAL_RES_KEY = "surge:approval_res:{req_id}"
_APPROVAL_PENDING_KEY = "surge:approval_pending:{approver}"


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
		row["locked"] = _is_locked(row["user"], pos_profile)
		row["lockout_until"] = _lockout_until(row["user"], pos_profile)

	return surge_response({"cashiers": rows})


@frappe.whitelist(allow_guest=False)
def verify_pin(pos_profile: str, user: str, pin: str) -> object:
	require_pos_profile_access(pos_profile)

	pin = (pin or "").strip()
	if len(pin) != 64 or not all(c in "0123456789abcdef" for c in pin):
		return surge_response({"status": "invalid", "message": "Invalid PIN format."})

	if _is_locked(user, pos_profile):
		return surge_response(
			{
				"status": "locked",
				"lockout_until": _lockout_until(user, pos_profile),
			}
		)

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
			return surge_response(
				{
					"status": "locked",
					"lockout_until": _lockout_until(user, pos_profile),
				}
			)
		return surge_response({"status": "wrong_pin", "attempts_left": remaining})

	_clear_attempts(user, pos_profile)
	full_name = frappe.db.get_value("User", user, "full_name")
	_log_action("cashier_login", user=user, profile=pos_profile)

	return surge_response(
		{
			"status": "ok",
			"user": user,
			"full_name": full_name,
			"access_level": row.access_level or "Cashier",
		}
	)


@frappe.whitelist(allow_guest=False)
def set_pin(user: str, pin: str, pos_profile: str) -> object:
	require_pos_profile_access(pos_profile)
	_require_manager_on_profile(pos_profile)

	pin = (pin or "").strip()
	if not pin.isdigit() or not (4 <= len(pin) <= 8):
		frappe.throw("PIN must be 4-8 numeric digits.", frappe.ValidationError)

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

	result = frappe.parse_json(verify_pin(pos_profile=pos_profile, user=supervisor, pin=supervisor_pin).data)
	if result.get("status") != "ok":
		return surge_response(result)

	access = (
		frappe.db.get_value(
			"POS Profile User",
			{"parent": pos_profile, "user": supervisor},
			"access_level",
		)
		or "Cashier"
	)

	if access not in ("Supervisor", "Manager"):
		return surge_response(
			{
				"status": "forbidden",
				"message": "Only Supervisors and Managers can override lockouts.",
			}
		)

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
		frappe.logger().warning(f"Surge: forgot_pin email failed for {user}")

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
			frappe.get_doc(
				{
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
				}
			).insert(ignore_permissions=True)
		except Exception:
			frappe.logger().warning(f"Surge: could not create notification for {notify_user}")

	frappe.db.commit()
	_log_action("forgot_pin", user=user, profile=pos_profile)

	return surge_response({"status": "ok"})


@frappe.whitelist(allow_guest=False)
def request_approval(pos_profile: str, approver: str, pin: str, action: str, meta: str = "") -> object:
	"""
	Verify approver PIN (must be Supervisor or Manager) and return a signed HMAC token.
	Token is one-time-use with a 5-minute TTL.
	"""
	require_pos_profile_access(pos_profile)

	pin = (pin or "").strip()
	if len(pin) != 64 or not all(c in "0123456789abcdef" for c in pin):
		return surge_response({"status": "invalid", "message": "Invalid PIN format."})

	row = frappe.db.get_value(
		"POS Profile User",
		{"parent": pos_profile, "user": approver, "status": "Active"},
		["access_level", "surge_pos_pin"],
		as_dict=True,
	)
	if not row:
		return surge_response({"status": "invalid", "message": "Approver not active on this profile."})

	if row.access_level not in ("Supervisor", "Manager"):
		return surge_response(
			{"status": "forbidden", "message": "Only Supervisors and Managers can approve."}
		)

	if not row.surge_pos_pin or pin != _hash_pin(row.surge_pos_pin):
		return surge_response({"status": "wrong_pin", "message": "Incorrect PIN."})

	payload = {
		"action": action,
		"approver": approver,
		"access_level": row.access_level,
		"profile": pos_profile,
		"ts": now_datetime().isoformat(),
		"meta": meta,
	}
	token = _sign_token(payload)

	token_hash = hashlib.sha256(token.encode()).hexdigest()
	try:
		frappe.cache().set_value(
			_TOKEN_KEY.format(token_hash=token_hash),
			"1",
			expires_in_sec=APPROVAL_TOKEN_TTL,
		)
	except Exception:
		frappe.logger().warning("Surge: Redis unavailable — approval token not stored in cache")

	_log_action(
		"approval_granted", user=approver, profile=pos_profile, by=frappe.session.user, new_value=action
	)
	return surge_response({"status": "ok", "token": token})


@frappe.whitelist(allow_guest=False)
def request_approval_remote(pos_profile: str, approver: str, action: str, meta: str = "") -> object:
	"""Cashier initiates a remote approval — stored in Redis, pushed to approver via realtime."""
	require_pos_profile_access(pos_profile)

	row = frappe.db.get_value(
		"POS Profile User",
		{"parent": pos_profile, "user": approver, "status": "Active"},
		["access_level"],
		as_dict=True,
	)
	if not row or row.access_level not in ("Supervisor", "Manager"):
		return surge_response({"status": "invalid", "message": "Approver not eligible."})

	req_id = str(_uuid.uuid4())
	cashier = frappe.session.user
	cashier_name = frappe.db.get_value("User", cashier, "full_name") or cashier

	payload = {
		"req_id": req_id,
		"cashier": cashier,
		"cashier_name": cashier_name,
		"approver": approver,
		"pos_profile": pos_profile,
		"action": action,
		"meta": meta,
		"created_at": now_datetime().isoformat(),
	}

	cache = frappe.cache()
	try:
		cache.set_value(_APPROVAL_REQ_KEY.format(req_id=req_id), payload, expires_in_sec=APPROVAL_TOKEN_TTL)
		pending_key = cache.make_key(_APPROVAL_PENDING_KEY.format(approver=approver))
		cache.execute_command("SADD", pending_key, req_id)
		cache.execute_command("EXPIRE", pending_key, APPROVAL_TOKEN_TTL)
	except Exception:
		# Redis unavailable — remote flow cannot work; tell cashier to use same-screen PIN
		return surge_response(
			{
				"status": "redis_unavailable",
				"message": "Remote approval is temporarily unavailable. Ask the manager to enter their PIN on this screen.",
			}
		)

	frappe.publish_realtime(
		"surge:approval_request",
		{"req_id": req_id, "cashier_name": cashier_name, "action": action, "pos_profile": pos_profile},
		user=approver,
		after_commit=False,
	)

	# Persistent notification so manager sees it on login even if they missed the realtime event
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": f"Approval request from {cashier_name}",
				"email_content": (
					f"<b>{cashier_name}</b> is requesting approval for "
					f"<b>{action.replace('_', ' ')}</b> on POS Profile <b>{pos_profile}</b>. "
					f"Open Surge POS to approve or deny."
				),
				"for_user": approver,
				"type": "Alert",
				"from_user": cashier,
				"document_type": "POS Profile",
				"document_name": pos_profile,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		pass

	return surge_response({"status": "pending", "req_id": req_id})


@frappe.whitelist(allow_guest=False)
def cancel_approval_request(req_id: str) -> object:
	"""Cashier cancels their own pending remote approval request."""
	cashier = frappe.session.user
	cache = frappe.cache()
	req_cache_key = _APPROVAL_REQ_KEY.format(req_id=req_id)

	req = cache.get_value(req_cache_key)
	if not req:
		return surge_response({"status": "ok"})  # already gone — nothing to do

	if isinstance(req, str):
		req = frappe.parse_json(req)

	if req.get("cashier") != cashier:
		return surge_response({"status": "forbidden"})

	approver = req.get("approver", "")
	pos_profile = req.get("pos_profile", "")

	try:
		cache.delete_value(req_cache_key)
		if approver:
			pending_key = cache.make_key(_APPROVAL_PENDING_KEY.format(approver=approver))
			cache.execute_command("SREM", pending_key, req_id)
	except Exception:
		pass

	if approver:
		frappe.publish_realtime(
			"surge:approval_cancelled",
			{"req_id": req_id},
			user=approver,
			after_commit=False,
		)

	_mark_approval_notification_read(approver=approver, cashier=cashier, pos_profile=pos_profile)
	return surge_response({"status": "ok"})


@frappe.whitelist(allow_guest=False)
def respond_to_approval(req_id: str, pin: str, decision: str) -> object:
	"""Approver enters their PIN to approve or deny a pending remote request."""
	approver = frappe.session.user

	pin = (pin or "").strip()
	if len(pin) != 64 or not all(c in "0123456789abcdef" for c in pin):
		return surge_response({"status": "invalid", "message": "Invalid PIN format."})

	cache = frappe.cache()
	req_cache_key = _APPROVAL_REQ_KEY.format(req_id=req_id)

	try:
		req = cache.get_value(req_cache_key)
	except Exception:
		return surge_response({"status": "error", "message": "Approval system temporarily unavailable."})

	if not req:
		return surge_response({"status": "expired", "message": "Request already processed or expired."})

	# parse_json handles both dict (already deserialized by frappe cache) and str
	if isinstance(req, str):
		req = frappe.parse_json(req)

	pos_profile = req["pos_profile"]

	row = frappe.db.get_value(
		"POS Profile User",
		{"parent": pos_profile, "user": approver, "status": "Active"},
		["access_level", "surge_pos_pin"],
		as_dict=True,
	)
	if not row or row.access_level not in ("Supervisor", "Manager"):
		return surge_response({"status": "forbidden"})

	if not row.surge_pos_pin or pin != _hash_pin(row.surge_pos_pin):
		return surge_response({"status": "wrong_pin", "message": "Incorrect PIN."})

	# Consume the request — delete only after PIN is verified to avoid consuming on wrong PIN
	try:
		cache.delete_value(req_cache_key)
	except Exception:
		pass

	try:
		pending_key = cache.make_key(_APPROVAL_PENDING_KEY.format(approver=approver))
		cache.execute_command("SREM", pending_key, req_id)
	except Exception:
		pass

	cashier_user = req["cashier"]

	cashier = req.get("cashier", cashier_user)
	_mark_approval_notification_read(approver=approver, cashier=cashier, pos_profile=pos_profile)

	if decision == "deny":
		res = {"status": "denied", "message": "Your discount request was denied."}
		cache.set_value(_APPROVAL_RES_KEY.format(req_id=req_id), res, expires_in_sec=120)
		frappe.publish_realtime(
			"surge:approval_response", {**res, "req_id": req_id}, user=cashier_user, after_commit=False
		)
		_log_action(
			"approval_denied", user=cashier_user, profile=pos_profile, by=approver, new_value=req["action"]
		)
		return surge_response({"status": "ok"})

	# Approve — issue HMAC token
	token_payload = {
		"action": req["action"],
		"approver": approver,
		"access_level": row.access_level,
		"profile": pos_profile,
		"ts": now_datetime().isoformat(),
		"meta": req.get("meta", ""),
	}
	token = _sign_token(token_payload)
	token_hash = hashlib.sha256(token.encode()).hexdigest()
	cache.set_value(_TOKEN_KEY.format(token_hash=token_hash), "1", expires_in_sec=APPROVAL_TOKEN_TTL)

	approver_name = frappe.db.get_value("User", approver, "full_name") or approver
	res = {"status": "approved", "token": token, "approver_name": approver_name}
	cache.set_value(_APPROVAL_RES_KEY.format(req_id=req_id), res, expires_in_sec=120)
	frappe.publish_realtime(
		"surge:approval_response", {**res, "req_id": req_id}, user=cashier_user, after_commit=False
	)

	_log_action(
		"approval_granted", user=cashier_user, profile=pos_profile, by=approver, new_value=req["action"]
	)
	return surge_response({"status": "ok"})


@frappe.whitelist(allow_guest=False)
def poll_approval(req_id: str) -> object:
	"""Cashier polls for approval result — fallback when Socket.IO is unavailable."""
	cache = frappe.cache()
	res = cache.get_value(_APPROVAL_RES_KEY.format(req_id=req_id))
	if res:
		return surge_response(res if isinstance(res, dict) else frappe.parse_json(res))
	req = cache.get_value(_APPROVAL_REQ_KEY.format(req_id=req_id))
	if req:
		return surge_response({"status": "pending"})
	return surge_response({"status": "expired"})


@frappe.whitelist(allow_guest=False)
def get_pending_approvals() -> object:
	"""Manager/Supervisor fetches their queue of pending approval requests."""
	approver = frappe.session.user
	cache = frappe.cache()
	try:
		pending_key = cache.make_key(_APPROVAL_PENDING_KEY.format(approver=approver))
		members = cache.execute_command("SMEMBERS", pending_key) or set()
	except Exception:
		return surge_response({"requests": []})

	requests = []
	for m in members:
		req_id = m.decode() if isinstance(m, bytes) else m
		req = cache.get_value(_APPROVAL_REQ_KEY.format(req_id=req_id))
		if req:
			requests.append(req if isinstance(req, dict) else frappe.parse_json(req))
		else:
			try:
				cache.execute_command("SREM", pending_key, m)
			except Exception:
				pass

	return surge_response({"requests": requests})


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


def _sign_token(payload: dict) -> str:
	secret = _get_hmac_secret()
	msg = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
	sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
	data = base64.urlsafe_b64encode(msg).decode()
	return f"{data}.{sig}"


def verify_approval_token(token: str) -> dict | None:
	"""Return payload dict if token is valid, unexpired, and unused. Consumes it."""
	try:
		parts = token.rsplit(".", 1)
		if len(parts) != 2:
			return None
		data, sig = parts

		msg = base64.urlsafe_b64decode(data + "==")
		secret = _get_hmac_secret()
		expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
		if not hmac.compare_digest(sig, expected):
			return None

		payload = json.loads(msg)

		# Enforce TTL
		from datetime import datetime

		ts = datetime.fromisoformat(payload["ts"])
		if (now_datetime() - ts).total_seconds() > APPROVAL_TOKEN_TTL:
			return None

		# One-time use via Redis
		token_hash = hashlib.sha256(token.encode()).hexdigest()
		redis_key = _TOKEN_KEY.format(token_hash=token_hash)
		try:
			if not frappe.cache().get_value(redis_key):
				return None
			frappe.cache().delete_value(redis_key)
		except Exception:
			# Redis unavailable — allow but log; prefer availability over strict replay prevention
			frappe.logger().warning("Surge: Redis unavailable — approval token replay check skipped")

		return payload
	except Exception:
		return None


def _get_hmac_secret() -> bytes:
	try:
		from frappe.utils.password import get_encryption_key

		key = get_encryption_key()
		return key.encode() if isinstance(key, str) else key
	except Exception:
		site = getattr(frappe.local, "site", "surge")
		pwd = frappe.conf.get("db_password", "") or "surge-secret"
		return hashlib.sha256(f"{site}:{pwd}".encode()).digest()


def _mark_approval_notification_read(approver: str, cashier: str, pos_profile: str) -> None:
	"""Mark pending approval Notification Log entries as read so Frappe bell clears."""
	try:
		notifications = frappe.get_all(
			"Notification Log",
			filters={
				"for_user": approver,
				"from_user": cashier,
				"document_type": "POS Profile",
				"document_name": pos_profile,
				"read": 0,
			},
			pluck="name",
			limit=10,
		)
		for name in notifications:
			frappe.db.set_value("Notification Log", name, "read", 1)
		if notifications:
			frappe.db.commit()
	except Exception:
		pass


def _log_action(
	action: str,
	user: str,
	profile: str,
	by: str | None = None,
	invoice: str | None = None,
	approver: str | None = None,
	old_value: str = "",
	new_value: str = "",
) -> None:
	try:
		frappe.logger().info(
			f"Surge audit | action={action} user={user} profile={profile} by={by or user} invoice={invoice}"
		)
	except Exception:
		pass

	try:
		if not frappe.db.table_exists("POS Security Audit Log"):
			return
		doc = frappe.new_doc("POS Security Audit Log")
		doc.action_type = action
		doc.user = user
		doc.pos_profile = profile
		doc.invoice = invoice
		doc.approver = approver or by
		doc.old_value = (old_value or "")[:140]
		doc.new_value = (new_value or "")[:140]
		doc.terminal_id = frappe.session.user
		try:
			doc.ip_address = frappe.request.remote_addr if frappe.request else ""
		except Exception:
			doc.ip_address = ""
		doc.insert(ignore_permissions=True, ignore_links=True)
	except Exception as e:
		frappe.logger().warning(f"Surge: audit log write failed: {e}")
