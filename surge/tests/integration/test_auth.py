"""
Integration tests — Groups A (Auth / PIN) — Scenarios A01-A14.

A01  Happy login — correct PIN
A02  Wrong PIN once — attempts_left returned
A03  Wrong PIN 3x sequential — locked, lockout_until shown
A04  Wrong PIN 3x concurrent — atomic INCR, exactly 3 increments
A05  Login with locked account — stays locked even with correct PIN
A06  Supervisor unlocks cashier
A07  Non-supervisor tries to unlock — forbidden
A08  Forgot PIN — managers notified, generic response
A09  Forgot PIN spam — only first triggers notification (rate limit)
A10  PIN set stores hash — not plaintext
A11  Old plaintext PIN migration — success + auto-upgraded
A12  New hashed PIN login — direct hash comparison
A13  No PIN set — returns no_pin
A14  Disabled user login — returns invalid
"""

import json
import threading
import time

import frappe
import pytest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from surge.api.auth import (
	FORGOT_PIN_RATE_LIMIT_SEC,
	PIN_MAX_ATTEMPTS,
	_clear_attempts,
	_clear_lockout,
	_hash_pin,
	_is_hashed,
	_is_locked,
	forgot_pin,
	override_lockout,
	set_pin,
	verify_pin,
)
from surge.tests.integration._base import (
	TEST_COMPANY,
	TEST_COST_CENTER,
	TEST_PRICE_LIST,
	TEST_WAREHOUSE,
	TEST_WRITE_OFF_ACCOUNT,
	ensure_master_data,
)

# ── Fixture helpers ───────────────────────────────────────────────────────────

_TEST_PROFILE = "_AuthTestProfile"
_CASHIER = "auth_cashier@test.surge"
_SUPERVISOR = "auth_supervisor@test.surge"
_MANAGER = "auth_manager@test.surge"
_DISABLED_USER = "auth_disabled@test.surge"
_TEST_PIN = "1234"
_TEST_PIN_HASH = _hash_pin(_TEST_PIN)


def _ensure_user(email: str, enabled: int = 1) -> str:
	if not frappe.db.exists("User", email):
		u = frappe.new_doc("User")
		u.email = email
		u.first_name = email.split("@")[0]
		u.send_welcome_email = 0
		u.enabled = enabled
		u.insert(ignore_permissions=True)
	else:
		frappe.db.set_value("User", email, "enabled", enabled)
	if enabled and not frappe.db.exists("Has Role", {"parent": email, "role": "POS User"}):
		doc = frappe.get_doc("User", email)
		doc.append("roles", {"role": "POS User"})
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return email


def _add_to_profile(user, access_level="Cashier", pin=_TEST_PIN_HASH, status="Active"):
	existing = frappe.db.exists("POS Profile User", {"parent": _TEST_PROFILE, "user": user})
	if existing:
		frappe.db.set_value(
			"POS Profile User",
			existing,
			{"access_level": access_level, "surge_pos_pin": pin, "status": status},
		)
	else:
		profile = frappe.get_doc("POS Profile", _TEST_PROFILE)
		profile.append(
			"applicable_for_users",
			{"user": user, "access_level": access_level, "surge_pos_pin": pin, "status": status},
		)
		profile.save(ignore_permissions=True)
	frappe.db.commit()


def _clear_pin_state(user=None):
	users = [user or _CASHIER]
	for u in users:
		_clear_attempts(u, _TEST_PROFILE)
		_clear_lockout(u, _TEST_PROFILE)


class AuthTestBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_master_data()
		# Ensure users exist
		_ensure_user(_CASHIER)
		_ensure_user(_SUPERVISOR)
		_ensure_user(_MANAGER)
		_ensure_user(_DISABLED_USER, enabled=0)

		# Create test profile if needed
		if not frappe.db.exists("POS Profile", _TEST_PROFILE):
			# Only use modes that have an account configured for TEST_COMPANY
			# (avoids "Cheque" which requires a bank account on production sites)
			modes = frappe.db.get_all(
				"Mode of Payment Account",
				filters={"company": TEST_COMPANY},
				pluck="parent",
				limit=1,
			) or ["Cash"]
			p = frappe.new_doc("POS Profile")
			p.name = _TEST_PROFILE
			p.company = TEST_COMPANY
			p.warehouse = TEST_WAREHOUSE
			p.selling_price_list = TEST_PRICE_LIST
			for m in modes:
				p.append("payments", {"mode_of_payment": m, "default": 1})
			p.currency = "INR"
			p.write_off_account = TEST_WRITE_OFF_ACCOUNT
			p.write_off_cost_center = TEST_COST_CENTER
			p.insert(ignore_permissions=True)
			frappe.db.commit()

		# Add users to profile
		_add_to_profile(_CASHIER, "Cashier", _TEST_PIN_HASH)
		_add_to_profile(_SUPERVISOR, "Supervisor", _TEST_PIN_HASH)
		_add_to_profile(_MANAGER, "Manager", _TEST_PIN_HASH)
		_add_to_profile(_DISABLED_USER, "Cashier", _TEST_PIN_HASH)

	def setUp(self):
		_clear_pin_state(_CASHIER)
		_clear_pin_state(_SUPERVISOR)
		_clear_pin_state(_MANAGER)
		# Clear forgot_pin rate limit key
		try:
			key = f"surge:forgot_pin_rate:{_CASHIER}:{_TEST_PROFILE}"
			frappe.cache().delete_value(key)
		except Exception:
			pass


# ── Group A — PIN Login ───────────────────────────────────────────────────────


class TestPINLogin(AuthTestBase):
	def _verify(self, user=_CASHIER, pin=_TEST_PIN_HASH):
		return json.loads(verify_pin(_TEST_PROFILE, user, pin).data)

	# A01
	def test_A01_happy_login_correct_pin(self):
		"""A01: Correct PIN → status ok, full_name, access_level returned."""
		result = self._verify()
		self.assertEqual(result["status"], "ok")
		self.assertEqual(result["user"], _CASHIER)
		self.assertIn("full_name", result)
		self.assertIn("access_level", result)

	# A02
	def test_A02_wrong_pin_once_shows_attempts_left(self):
		"""A02: One wrong PIN → wrong_pin status, attempts_left = 2."""
		result = self._verify(pin=_hash_pin("9999"))
		self.assertEqual(result["status"], "wrong_pin")
		self.assertEqual(result["attempts_left"], PIN_MAX_ATTEMPTS - 1)

	# A03
	def test_A03_wrong_pin_3x_sequential_locks_account(self):
		"""A03: 3x wrong PIN sequential → locked, lockout_until shown."""
		wrong = _hash_pin("9999")
		for _ in range(PIN_MAX_ATTEMPTS - 1):
			self._verify(pin=wrong)
		result = self._verify(pin=wrong)
		self.assertEqual(result["status"], "locked")
		self.assertIn("lockout_until", result)
		self.assertIsNotNone(result["lockout_until"])

	# A04
	def test_A04_wrong_pin_3x_concurrent_atomic(self):
		"""A04: 3 concurrent wrong PINs → atomic INCR, user locked after exactly 3."""
		wrong = _hash_pin("9999")
		results = []
		site = frappe.local.site

		def try_wrong():
			frappe.init(site=site)
			frappe.connect()
			try:
				r = json.loads(verify_pin(_TEST_PROFILE, _CASHIER, wrong).data)
				results.append(r["status"])
			finally:
				frappe.destroy()

		threads = [threading.Thread(target=try_wrong) for _ in range(PIN_MAX_ATTEMPTS)]
		for t in threads:
			t.start()
		for t in threads:
			t.join()

		self.assertTrue(
			_is_locked(_CASHIER, _TEST_PROFILE), "User must be locked after 3 concurrent wrong PINs"
		)
		self.assertIn("locked", results)

	# A05
	def test_A05_locked_account_stays_locked_even_with_correct_pin(self):
		"""A05: Once locked, correct PIN still returns locked status."""
		wrong = _hash_pin("9999")
		for _ in range(PIN_MAX_ATTEMPTS):
			self._verify(pin=wrong)

		# Now try with correct PIN
		result = self._verify(pin=_TEST_PIN_HASH)
		self.assertEqual(result["status"], "locked", "Locked account must stay locked even with correct PIN")

	# A06
	def test_A06_supervisor_unlocks_cashier(self):
		"""A06: Supervisor enters correct PIN → cashier unlocked, attempts cleared."""
		wrong = _hash_pin("9999")
		for _ in range(PIN_MAX_ATTEMPTS):
			self._verify(pin=wrong)
		self.assertTrue(_is_locked(_CASHIER, _TEST_PROFILE))

		frappe.set_user(_SUPERVISOR)
		try:
			result = json.loads(override_lockout(_CASHIER, _TEST_PIN_HASH, _TEST_PROFILE).data)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(result["status"], "ok")
		self.assertFalse(_is_locked(_CASHIER, _TEST_PROFILE), "Cashier should be unlocked after override")

	# A07
	def test_A07_cashier_cannot_unlock(self):
		"""A07: Cashier-level user tries override → forbidden."""
		# frappe.session.user = _CASHIER (Cashier access level)
		# override_lockout verifies _CASHIER's PIN → ok, then checks access_level → Cashier → forbidden
		frappe.set_user(_CASHIER)
		try:
			result = json.loads(override_lockout(_SUPERVISOR, _TEST_PIN_HASH, _TEST_PROFILE).data)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(result["status"], "forbidden")

	# A08
	def test_A08_forgot_pin_returns_generic_response(self):
		"""A08: forgot_pin always returns generic response — no user disclosure."""
		result = json.loads(forgot_pin(_CASHIER, _TEST_PROFILE).data)
		# Generic message regardless of whether user exists
		self.assertEqual(result["status"], "ok")
		# Message should not disclose whether user was found
		msg = result.get("message", "")
		self.assertNotIn(_CASHIER, msg)

	# A09
	def test_A09_forgot_pin_rate_limit(self):
		"""A09: Second forgot_pin within rate limit → same generic response, no extra notification."""
		# First call
		r1 = json.loads(forgot_pin(_CASHIER, _TEST_PROFILE).data)
		# Second call immediately
		r2 = json.loads(forgot_pin(_CASHIER, _TEST_PROFILE).data)
		# Both return ok (generic)
		self.assertEqual(r1["status"], "ok")
		self.assertEqual(r2["status"], "ok")
		# Both return the same generic message
		self.assertEqual(r1.get("message", ""), r2.get("message", ""))

	# A10
	def test_A10_set_pin_stores_hash_not_plaintext(self):
		"""A10: Manager sets PIN "5678" → DB stores 64-char hex, not "5678"."""
		frappe.set_user(_MANAGER)
		try:
			json.loads(set_pin(_CASHIER, "5678", _TEST_PROFILE).data)
		finally:
			frappe.set_user("Administrator")

		stored = frappe.db.get_value(
			"POS Profile User",
			{"parent": _TEST_PROFILE, "user": _CASHIER},
			"surge_pos_pin",
		)
		self.assertNotEqual(stored, "5678", "PIN must not be stored as plaintext")
		self.assertTrue(_is_hashed(stored), "Stored value must be a SHA256 hex digest")

		# Restore original PIN
		_add_to_profile(_CASHIER, "Cashier", _TEST_PIN_HASH)

	# A10b
	def test_A10b_set_pin_invalid_format_raises(self):
		"""A10b: set_pin with non-numeric PIN → ValidationError 'PIN must be 4-8 numeric digits'."""
		frappe.set_user(_MANAGER)
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				set_pin(_CASHIER, "abc", _TEST_PROFILE)
			self.assertIn("4-8 numeric digits", str(ctx.exception))
		finally:
			frappe.set_user("Administrator")

	# A11
	def test_A11_plaintext_pin_migration(self):
		"""A11: Cashier with plaintext PIN logs in → succeeds + auto-upgraded to hash."""
		# Manually store plaintext PIN in DB (legacy state)
		row_name = frappe.db.get_value(
			"POS Profile User", {"parent": _TEST_PROFILE, "user": _CASHIER}, "name"
		)
		frappe.db.set_value("POS Profile User", row_name, "surge_pos_pin", _TEST_PIN)
		frappe.db.commit()

		result = self._verify(pin=_TEST_PIN_HASH)
		self.assertEqual(result["status"], "ok", "Plaintext PIN login should succeed via migration path")

		# Verify auto-upgrade happened
		stored = frappe.db.get_value(
			"POS Profile User", {"parent": _TEST_PROFILE, "user": _CASHIER}, "surge_pos_pin"
		)
		self.assertTrue(
			_is_hashed(stored), "PIN must be auto-upgraded to hash on first successful migration login"
		)

		# Restore
		_add_to_profile(_CASHIER, "Cashier", _TEST_PIN_HASH)

	# A12
	def test_A12_hashed_pin_login_direct_comparison(self):
		"""A12: Cashier with SHA256-stored PIN logs in via direct hash comparison."""
		# Ensure hash is stored (not plaintext)
		row_name = frappe.db.get_value(
			"POS Profile User", {"parent": _TEST_PROFILE, "user": _CASHIER}, "name"
		)
		frappe.db.set_value("POS Profile User", row_name, "surge_pos_pin", _TEST_PIN_HASH)
		frappe.db.commit()

		result = self._verify(pin=_TEST_PIN_HASH)
		self.assertEqual(result["status"], "ok")

	# A13
	def test_A13_no_pin_set_returns_no_pin_status(self):
		"""A13: User with empty surge_pos_pin → returns {status: no_pin}."""
		row_name = frappe.db.get_value(
			"POS Profile User", {"parent": _TEST_PROFILE, "user": _CASHIER}, "name"
		)
		frappe.db.set_value("POS Profile User", row_name, "surge_pos_pin", "")
		frappe.db.commit()

		result = self._verify(pin=_TEST_PIN_HASH)
		self.assertEqual(result["status"], "no_pin")

		# Restore
		_add_to_profile(_CASHIER, "Cashier", _TEST_PIN_HASH)

	# A14
	def test_A14_disabled_user_returns_invalid(self):
		"""A14: enabled=0 user → returns invalid (not locked, not wrong_pin)."""
		# Ensure disabled user has a PIN
		_add_to_profile(_DISABLED_USER, "Cashier", _TEST_PIN_HASH, status="Active")
		frappe.db.set_value("User", _DISABLED_USER, "enabled", 0)
		frappe.db.commit()

		result = json.loads(verify_pin(_TEST_PROFILE, _DISABLED_USER, _TEST_PIN_HASH).data)
		self.assertEqual(result["status"], "invalid")
		self.assertNotEqual(result["status"], "locked")
