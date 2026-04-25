"""
Integration tests — Group G (Permission Guards) — Scenarios G01-G11.

G01  Guest user → AuthenticationError (require_pos_role blocks)
G02  Open profile (no user rows) → any POS User allowed
G03  User not listed on restricted profile → PermissionError
G04  Active user listed → allowed
G05  Inactive user listed → PermissionError
G06  Profile with only Inactive rows → all users denied
G07  Cross-terminal warehouse (user not on that profile's warehouse) → PermissionError
G08  Administrator bypasses all profile checks
G09  System Manager bypasses Surge Manager guard
G10  Manager-level user passes require_surge_manager_role
G11  Supervisor-level user fails require_surge_manager_role (Supervisor ≠ Manager)
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from surge.tests.integration._base import ensure_master_data
from surge.utils.permissions import (
	require_pos_profile_access,
	require_surge_manager_role,
	require_warehouse_access,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_OPEN_PROFILE = "_GPermOpenProfile"
_RESTRICTED_PROFILE = "_GPermRestrictedProfile"
_ALT_PROFILE = "_GPermAltProfile"

_ACTIVE_USER = "g_active@test.surge"
_INACTIVE_USER = "g_inactive@test.surge"
_UNLISTED_USER = "g_unlisted@test.surge"
_MANAGER_USER = "g_manager@test.surge"
_SUPERVISOR_USER = "g_supervisor@test.surge"
_SYSMANAGER_USER = "g_sysmanager@test.surge"


def _ensure_user(email, enabled=1, roles=None):
	if not frappe.db.exists("User", email):
		u = frappe.new_doc("User")
		u.email = email
		u.first_name = email.split("@")[0]
		u.send_welcome_email = 0
		u.enabled = enabled
		u.insert(ignore_permissions=True)
	else:
		frappe.db.set_value("User", email, "enabled", enabled)
	for role in roles or ["POS User"]:
		if not frappe.db.exists("Has Role", {"parent": email, "role": role}):
			doc = frappe.get_doc("User", email)
			doc.append("roles", {"role": role})
			doc.save(ignore_permissions=True)
	frappe.db.commit()


def _make_profile(name, users=None, warehouse=None):
	ensure_master_data()
	if frappe.db.exists("POS Profile", name):
		frappe.delete_doc("POS Profile", name, ignore_permissions=True, force=True)
		frappe.db.commit()
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	wh = warehouse or frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")
	p = frappe.new_doc("POS Profile")
	p.name = name
	p.company = company
	p.warehouse = wh
	p.selling_price_list = frappe.db.get_value("Price List", {"buying": 0}, "name")
	for m in frappe.get_all("Mode of Payment", limit=1, pluck="name"):
		p.append("payments", {"mode_of_payment": m})
	for u in users or []:
		p.append(
			"applicable_for_users",
			{
				"user": u["user"],
				"status": u.get("status", "Active"),
				"access_level": u.get("access_level", "Cashier"),
			},
		)
	p.insert(ignore_permissions=True)
	frappe.db.commit()
	return p


class PermissionsTestBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for email in [_ACTIVE_USER, _INACTIVE_USER, _UNLISTED_USER]:
			_ensure_user(email)
		_ensure_user(_MANAGER_USER)
		_ensure_user(_SUPERVISOR_USER)
		_ensure_user(_SYSMANAGER_USER, roles=["POS User", "System Manager"])

		_make_profile(_OPEN_PROFILE, users=[])
		_make_profile(
			_RESTRICTED_PROFILE,
			users=[
				{"user": _ACTIVE_USER, "status": "Active", "access_level": "Cashier"},
				{"user": _INACTIVE_USER, "status": "Inactive", "access_level": "Cashier"},
				{"user": _MANAGER_USER, "status": "Active", "access_level": "Manager"},
				{"user": _SUPERVISOR_USER, "status": "Active", "access_level": "Supervisor"},
			],
		)

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		for name in [_OPEN_PROFILE, _RESTRICTED_PROFILE]:
			if frappe.db.exists("POS Profile", name):
				frappe.delete_doc("POS Profile", name, ignore_permissions=True, force=True)
		frappe.db.commit()


# ── G01-G06: Profile access guard ────────────────────────────────────────────


class TestProfileAccess(PermissionsTestBase):
	def test_G01_guest_raises_authentication_error(self):
		"""G01: Guest session → AuthenticationError before profile check even starts."""
		frappe.session.user = "Guest"
		try:
			with self.assertRaises(frappe.AuthenticationError):
				require_pos_profile_access(_OPEN_PROFILE)
		finally:
			frappe.session.user = "Administrator"

	def test_G02_open_profile_allows_any_pos_user(self):
		"""G02: Profile with no user rows → all POS-role holders pass."""
		frappe.set_user(_ACTIVE_USER)
		try:
			require_pos_profile_access(_OPEN_PROFILE)  # must not raise
		finally:
			frappe.set_user("Administrator")

	def test_G03_unlisted_user_on_restricted_profile_denied(self):
		"""G03: User not listed on restricted profile → PermissionError."""
		frappe.set_user(_UNLISTED_USER)
		try:
			with self.assertRaises(frappe.PermissionError):
				require_pos_profile_access(_RESTRICTED_PROFILE)
		finally:
			frappe.set_user("Administrator")

	def test_G04_active_listed_user_allowed(self):
		"""G04: Active user listed on profile → passes guard."""
		frappe.set_user(_ACTIVE_USER)
		try:
			require_pos_profile_access(_RESTRICTED_PROFILE)  # must not raise
		finally:
			frappe.set_user("Administrator")

	def test_G05_inactive_listed_user_denied(self):
		"""G05: Inactive user listed on profile → PermissionError."""
		frappe.set_user(_INACTIVE_USER)
		try:
			with self.assertRaises(frappe.PermissionError):
				require_pos_profile_access(_RESTRICTED_PROFILE)
		finally:
			frappe.set_user("Administrator")

	def test_G06_all_inactive_profile_denies_everyone(self):
		"""G06: Profile with only Inactive rows → any non-Admin user is denied."""
		all_inactive = "_GPermAllInactive"
		_make_profile(
			all_inactive,
			users=[
				{"user": _ACTIVE_USER, "status": "Inactive"},
			],
		)
		frappe.set_user(_ACTIVE_USER)
		try:
			with self.assertRaises(frappe.PermissionError):
				require_pos_profile_access(all_inactive)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("POS Profile", all_inactive, ignore_permissions=True, force=True)
			frappe.db.commit()


# ── G07: Cross-terminal warehouse guard ──────────────────────────────────────


class TestWarehouseAccess(PermissionsTestBase):
	def test_G07_cross_terminal_warehouse_denied(self):
		"""G07: Warehouse linked only to a profile the user cannot access → PermissionError."""
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		# Pick any warehouse — make a locked profile so _UNLISTED_USER cannot access it
		wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")
		_make_profile(
			"_GPermWHProfile",
			warehouse=wh,
			users=[
				{"user": _ACTIVE_USER, "status": "Active"},
			],
		)
		frappe.set_user(_UNLISTED_USER)
		try:
			with self.assertRaises(frappe.PermissionError):
				require_warehouse_access(wh)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("POS Profile", "_GPermWHProfile", ignore_permissions=True, force=True)
			frappe.db.commit()


# ── G08-G11: Manager-level guards ────────────────────────────────────────────


class TestManagerGuard(PermissionsTestBase):
	def test_G08_administrator_bypasses_profile_access(self):
		"""G08: Administrator session → bypasses require_pos_profile_access entirely."""
		frappe.session.user = "Administrator"
		require_pos_profile_access(_RESTRICTED_PROFILE)  # must not raise

	def test_G09_system_manager_bypasses_surge_manager_guard(self):
		"""G09: System Manager role → passes require_surge_manager_role."""
		frappe.set_user(_SYSMANAGER_USER)
		try:
			require_surge_manager_role()  # must not raise
		finally:
			frappe.set_user("Administrator")

	def test_G10_manager_level_passes_surge_manager_guard(self):
		"""G10: Manager access_level on any active profile → passes guard."""
		frappe.set_user(_MANAGER_USER)
		try:
			require_surge_manager_role()  # must not raise
		finally:
			frappe.set_user("Administrator")

	def test_G11_supervisor_level_fails_surge_manager_guard(self):
		"""G11: Supervisor access_level is NOT Manager → require_surge_manager_role raises."""
		frappe.set_user(_SUPERVISOR_USER)
		try:
			with self.assertRaises(frappe.PermissionError):
				require_surge_manager_role()
		finally:
			frappe.set_user("Administrator")
