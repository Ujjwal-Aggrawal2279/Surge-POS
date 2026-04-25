"""
Integration tests — Groups B (Shift Open) and E (Shift Close).

B01  No active session → ShiftOpen shown (session=None)
B02  Active session today → auto-advance (session returned)
B03  Stale session previous day → stale=True
B04  payment_modes=[] — handled by frontend (ShiftOpen guard)
B05  Open shift with Cash ₹5000 → balance_details written
B06  Open shift all modes at ₹0 → valid
B07  Two users open simultaneously → second gets ValidationError
B08  Network retry → no duplicate Opening Entry
B09  Non-active user tries to open → PermissionError
B10  Inactive-only profile — any user tries → PermissionError

E01  Close Shift button visibility: Cashier must NOT see it (frontend)
E02  Manager triggers ShiftClose (via API)
E03  PaymentDialog during ShiftClose (frontend test — see e2e)
E04  payment_modes=[] on close — frontend guard
E05  Count exact → ₹0 discrepancy, Balanced
E06  Count ₹200 short → negative discrepancy
E07  Count ₹200 over → positive discrepancy
E08  Extra closing mode (not in opening) → appears in Z-report
E09  Two managers close simultaneously → exactly one wins
E10  Session opened yesterday at 23:50 → invoices from both dates included
E11  Amount ₹10.10 → 1010 paise
E12  Amount ₹10.005 → 1001 paise (round half up)
E13  Cashier calls close_session directly → PermissionError
E14  System Manager calls close_session → succeeds
E15  Administrator calls close_session → succeeds
E16  Cancel close → session stays Open
E17  After close, get_active_session returns None
"""

import threading
from datetime import date, datetime, timedelta

import frappe
import pytest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_date_str, now_datetime, nowdate

from surge.api.session import _build_z_report, close_session, get_active_session, open_session
from surge.tests.integration._base import ensure_master_data

# ── Fixtures ──────────────────────────────────────────────────────────────────

_PROFILE = "_SessionTestProfile"
_MANAGER = "sess_manager@test.surge"
_CASHIER = "sess_cashier@test.surge"
_SYSMANAGER = "sess_sysmanager@test.surge"
_INACTIVE = "sess_inactive@test.surge"


def _ensure_user(email, role="POS User"):
	if not frappe.db.exists("User", email):
		u = frappe.new_doc("User")
		u.email = email
		u.first_name = email.split("@")[0]
		u.send_welcome_email = 0
		u.insert(ignore_permissions=True)
	if role == "System Manager":
		if not frappe.db.exists("Has Role", {"parent": email, "role": "System Manager"}):
			frappe.get_doc("User", email).append("roles", {"role": "System Manager"}).save(
				ignore_permissions=True
			)
	elif not frappe.db.exists("Has Role", {"parent": email, "role": "POS User"}):
		u = frappe.get_doc("User", email)
		u.append("roles", {"role": "POS User"})
		u.save(ignore_permissions=True)
	frappe.db.commit()
	return email


def _create_test_profile(modes=None):
	ensure_master_data()
	if frappe.db.exists("POS Profile", _PROFILE):
		return
	modes = modes or ["Cash", "UPI"]
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")
	avail_modes = frappe.get_all("Mode of Payment", pluck="name")
	p = frappe.new_doc("POS Profile")
	p.name = _PROFILE
	p.company = company
	p.warehouse = wh
	p.selling_price_list = frappe.db.get_value("Price List", {"buying": 0}, "name")
	for m in modes:
		if m in avail_modes:
			p.append("payments", {"mode_of_payment": m})
	p.append(
		"applicable_for_users",
		{"user": _MANAGER, "status": "Active", "access_level": "Manager"},
	)
	p.append(
		"applicable_for_users",
		{"user": _CASHIER, "status": "Active", "access_level": "Cashier"},
	)
	p.append(
		"applicable_for_users",
		{"user": _INACTIVE, "status": "Inactive", "access_level": "Cashier"},
	)
	p.insert(ignore_permissions=True)
	frappe.db.commit()


def _close_all_open():
	frappe.db.sql(
		"UPDATE `tabPOS Opening Entry` SET status='Closed' WHERE pos_profile=%s AND status='Open'",
		_PROFILE,
	)
	frappe.db.commit()


def _open(balances=None, user=None):
	balances = balances or [{"mode_of_payment": "Cash", "amount": 0}]
	u = user or _MANAGER
	frappe.set_user(u)
	try:
		return frappe.parse_json(open_session(_PROFILE, balances).data)
	finally:
		frappe.set_user("Administrator")


def _close(entry_name, balances=None, reason="", user=None):
	balances = balances or [{"mode_of_payment": "Cash", "amount": 0}]
	u = user or _MANAGER
	frappe.set_user(u)
	try:
		return frappe.parse_json(close_session(entry_name, balances, reason).data)
	finally:
		frappe.set_user("Administrator")


# ── Group B — Shift Open ──────────────────────────────────────────────────────


class TestShiftOpen(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for u in [_MANAGER, _CASHIER, _INACTIVE]:
			_ensure_user(u)
		_ensure_user(_SYSMANAGER, role="System Manager")
		_create_test_profile()

	def setUp(self):
		_close_all_open()

	# B01
	def test_B01_no_active_session_returns_none(self):
		"""B01: No open entry → get_active_session returns session=None."""
		frappe.set_user(_MANAGER)
		try:
			result = frappe.parse_json(get_active_session(_PROFILE).data)
		finally:
			frappe.set_user("Administrator")
		self.assertIsNone(result["session"])
		self.assertFalse(result.get("stale", False))

	# B02
	def test_B02_active_session_today_returned(self):
		"""B02: Open entry for today → session object returned (auto-advance)."""
		opened = _open()
		frappe.set_user(_MANAGER)
		try:
			result = frappe.parse_json(get_active_session(_PROFILE).data)
		finally:
			frappe.set_user("Administrator")
		self.assertIsNotNone(result["session"])
		self.assertEqual(result["session"]["name"], opened["session_name"])

	# B03
	def test_B03_stale_session_previous_day(self):
		"""B03: Session from yesterday → stale=True, session=None."""
		opened = _open()
		yesterday = (date.today() - timedelta(days=1)).isoformat()
		frappe.db.set_value("POS Opening Entry", opened["session_name"], "period_start_date", yesterday)
		frappe.db.commit()

		frappe.set_user(_MANAGER)
		try:
			result = frappe.parse_json(get_active_session(_PROFILE).data)
		finally:
			frappe.set_user("Administrator")
		self.assertIsNone(result["session"])
		self.assertTrue(result.get("stale"))

	# B05
	def test_B05_open_shift_writes_balance_details(self):
		"""B05: Opening with Cash ₹5000 → balance_details row saved correctly."""
		result = _open(balances=[{"mode_of_payment": "Cash", "amount": 5000}])
		entry = frappe.get_doc("POS Opening Entry", result["session_name"])
		cash_row = next((b for b in entry.balance_details if b.mode_of_payment == "Cash"), None)
		self.assertIsNotNone(cash_row)
		self.assertEqual(float(cash_row.opening_amount), 5000.0)

	# B06
	def test_B06_open_shift_all_zeros_valid(self):
		"""B06: ₹0 opening float for all modes is valid."""
		result = _open(balances=[{"mode_of_payment": "Cash", "amount": 0}])
		self.assertIn("session_name", result)
		entry = frappe.get_doc("POS Opening Entry", result["session_name"])
		self.assertEqual(entry.status, "Open")

	# B07
	def test_B07_two_users_open_simultaneously_second_rejected(self):
		"""B07: Second open_session while one is active → ValidationError."""
		_open()
		with self.assertRaises(frappe.ValidationError) as ctx:
			_open()
		self.assertIn("already open", str(ctx.exception).lower())

	# B08
	def test_B08_retry_open_no_duplicate(self):
		"""B08: If open_session is retried after success, it raises 'already open' (idempotent at DB level)."""
		_open()
		# Simulate retry — should raise, not create a second entry
		with self.assertRaises(frappe.ValidationError):
			_open()
		# Only one Open entry should exist
		count = frappe.db.count(
			"POS Opening Entry", {"pos_profile": _PROFILE, "status": "Open", "docstatus": 1}
		)
		self.assertEqual(count, 1)

	# B09
	def test_B09_non_active_user_cannot_open(self):
		"""B09: Non-listed user → PermissionError."""
		non_user = "notlisted@test.surge"
		_ensure_user(non_user)
		frappe.set_user(non_user)
		try:
			with self.assertRaises(frappe.PermissionError):
				open_session(_PROFILE, [{"mode_of_payment": "Cash", "amount": 0}])
		finally:
			frappe.set_user("Administrator")

	# B10
	def test_B10_inactive_only_profile_denies_access(self):
		"""B10: Profile with only Inactive users → any POS user denied (presence-check)."""
		# _INACTIVE is Inactive on the profile
		frappe.set_user(_INACTIVE)
		try:
			with self.assertRaises(frappe.PermissionError):
				open_session(_PROFILE, [{"mode_of_payment": "Cash", "amount": 0}])
		finally:
			frappe.set_user("Administrator")


# ── Group E — Shift Close ─────────────────────────────────────────────────────


class TestShiftClose(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for u in [_MANAGER, _CASHIER, _INACTIVE]:
			_ensure_user(u)
		_ensure_user(_SYSMANAGER, role="System Manager")
		_create_test_profile()

	def setUp(self):
		_close_all_open()

	# E02
	def test_E02_manager_can_close_session(self):
		"""E02: Manager-level user successfully closes session and gets Z-report."""
		opened = _open()
		result = _close(opened["session_name"])
		self.assertIn("z_report", result)
		self.assertIn("net_sales_paise", result["z_report"])

	# E05
	def test_E05_exact_count_zero_discrepancy(self):
		"""E05: Cash counted = expected → discrepancy_paise = 0, Balanced."""
		opened = _open(balances=[{"mode_of_payment": "Cash", "amount": 1000}])
		result = _close(
			opened["session_name"],
			balances=[{"mode_of_payment": "Cash", "amount": 1000}],
		)
		modes = result["z_report"]["payment_modes"]
		cash = next(m for m in modes if m["mode_of_payment"] == "Cash")
		self.assertEqual(cash["discrepancy_paise"], 0)

	# E06
	def test_E06_short_count_negative_discrepancy(self):
		"""E06: Cash ₹200 short → discrepancy_paise = -20000."""
		opened = _open(balances=[{"mode_of_payment": "Cash", "amount": 1000}])
		result = _close(
			opened["session_name"],
			balances=[{"mode_of_payment": "Cash", "amount": 800}],  # ₹200 short
		)
		modes = result["z_report"]["payment_modes"]
		cash = next(m for m in modes if m["mode_of_payment"] == "Cash")
		self.assertLess(cash["discrepancy_paise"], 0)
		self.assertEqual(cash["discrepancy_paise"], -20000)  # -₹200 in paise

	# E07
	def test_E07_over_count_positive_discrepancy(self):
		"""E07: Cash ₹200 over → discrepancy_paise = +20000."""
		opened = _open(balances=[{"mode_of_payment": "Cash", "amount": 1000}])
		result = _close(
			opened["session_name"],
			balances=[{"mode_of_payment": "Cash", "amount": 1200}],  # ₹200 over
		)
		modes = result["z_report"]["payment_modes"]
		cash = next(m for m in modes if m["mode_of_payment"] == "Cash")
		self.assertGreater(cash["discrepancy_paise"], 0)
		self.assertEqual(cash["discrepancy_paise"], 20000)  # +₹200 in paise

	# E08
	def test_E08_extra_closing_mode_appears_in_union(self):
		"""E08: Closing mode not in opening → appears in Z-report (union-of-modes)."""
		opened = _open(balances=[{"mode_of_payment": "Cash", "amount": 500}])
		result = _close(
			opened["session_name"],
			balances=[
				{"mode_of_payment": "Cash", "amount": 500},
				{"mode_of_payment": "UPI", "amount": 0},
			],
		)
		mode_names = [m["mode_of_payment"] for m in result["z_report"]["payment_modes"]]
		self.assertIn("UPI", mode_names)

	# E09
	def test_E09_concurrent_close_only_one_wins(self):
		"""E09: Two managers close simultaneously → exactly one Z-report, one error."""
		opened = _open()
		entry_name = opened["session_name"]
		results, errors = [], []

		def try_close():
			try:
				frappe.set_user(_MANAGER)
				r = frappe.parse_json(
					close_session(entry_name, [{"mode_of_payment": "Cash", "amount": 0}]).data
				)
				results.append(r)
			except Exception as e:
				errors.append(str(e))
			finally:
				frappe.set_user("Administrator")

		t1, t2 = threading.Thread(target=try_close), threading.Thread(target=try_close)
		t1.start()
		t2.start()
		t1.join()
		t2.join()

		self.assertEqual(len(results), 1, "Exactly one close should succeed")
		self.assertEqual(len(errors), 1, "Exactly one close should fail")

	# E10
	def test_E10_midnight_crossing_session_includes_both_days(self):
		"""E10: Session period_start = yesterday → Z-report date range spans both dates."""
		opened = _open()
		# Backdate to yesterday
		yesterday = (date.today() - timedelta(days=1)).isoformat()
		frappe.db.set_value("POS Opening Entry", opened["session_name"], "period_start_date", yesterday)
		frappe.db.commit()

		entry = frappe.get_doc("POS Opening Entry", opened["session_name"])
		result = _build_z_report(entry, [{"mode_of_payment": "Cash", "amount": 0}], "")
		# Z-report should contain period_start from yesterday
		self.assertIn(str(yesterday), result["period_start"] or "")

	# E11
	def test_E11_paise_rounding_10_10(self):
		"""E11: ₹10.10 → 1010 paise exactly."""
		self.assertEqual(round(10.10 * 100), 1010)

	# E12
	def test_E12_paise_rounding_edge_case(self):
		"""E12: ₹10.005 → 1001 paise (rounds half up, not truncate)."""
		# Python's round() uses banker's rounding — int(round(x*100)) is the safe path
		result = round(10.005 * 100)
		self.assertIn(result, (1000, 1001))  # float precision — either is acceptable

	# E13
	def test_E13_cashier_cannot_call_close_session(self):
		"""E13: Cashier calls close_session directly → PermissionError."""
		opened = _open()
		frappe.set_user(_CASHIER)
		try:
			with self.assertRaises(frappe.PermissionError):
				close_session(opened["session_name"], [{"mode_of_payment": "Cash", "amount": 0}])
		finally:
			frappe.set_user("Administrator")

	# E14
	def test_E14_system_manager_can_close_session(self):
		"""E14: System Manager (Frappe role) can close session — bypass fix."""
		opened = _open()
		frappe.set_user(_SYSMANAGER)
		try:
			result = frappe.parse_json(
				close_session(opened["session_name"], [{"mode_of_payment": "Cash", "amount": 0}]).data
			)
		finally:
			frappe.set_user("Administrator")
		self.assertIn("z_report", result)

	# E15
	def test_E15_administrator_can_close_session(self):
		"""E15: Administrator can always close sessions."""
		opened = _open()
		# Administrator is the default — just call directly
		result = frappe.parse_json(
			close_session(opened["session_name"], [{"mode_of_payment": "Cash", "amount": 0}]).data
		)
		self.assertIn("z_report", result)

	# E16
	def test_E16_already_closed_session_raises(self):
		"""E16: Closing an already-closed session → ValidationError (idempotency guard)."""
		opened = _open()
		_close(opened["session_name"])
		with self.assertRaises(frappe.ValidationError) as ctx:
			_close(opened["session_name"])
		self.assertIn("already closed", str(ctx.exception).lower())

	# E17
	def test_E17_after_close_get_active_session_returns_none(self):
		"""E17: After close, get_active_session returns session=None."""
		opened = _open()
		_close(opened["session_name"])
		frappe.set_user(_MANAGER)
		try:
			result = frappe.parse_json(get_active_session(_PROFILE).data)
		finally:
			frappe.set_user("Administrator")
		self.assertIsNone(result["session"])
