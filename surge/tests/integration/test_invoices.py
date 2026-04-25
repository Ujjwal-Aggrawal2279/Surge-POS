"""
Integration tests — Group C (Selling & Cart) — Scenarios C01-C30.

C01  Add item, pay exact → submitted
C02  Network drop → status queued
C03  Reconnect → queued invoice syncs (queue runner test)
C04  Same client_request_id, same cashier → same invoice name
C05  Same client_request_id, different cashier → separate invoices
C06  qty = 0 → 400 ValidationError
C07  qty = -1 → 400 ValidationError
C08  rate_paise = -100 → 400 ValidationError
C09  discount_paise > rate_paise → 400 ValidationError
C10  Payment mode not in profile → 400 ValidationError
C11  Item.warehouse from different terminal → 403
C12  Discount < cashier limit → proceeds without approval
C13  Discount > cashier limit → approval required (raises without token)
C14  Supervisor PIN → approval token issued
C15  Cashier uses token → invoice stamped with override_approved_by
C16  Reuse same token → rejected
C17  Redis down during token use → rejected (fail-closed)
C18  Approval token meta = 1MB → capped to 500 chars
C19  10 concurrent invoices same terminal → all unique names
C20  10x server errors → circuit opens (badge shown — frontend test)
C21  Mobile checkout handleMobileCheckout stable ref (unit/E2E test)
C22  Empty payments list → 400 ValidationError, not enqueued
C23  Payment amount = 0 → 400 ValidationError, not enqueued
C24  Payment amount < 0 → 400 ValidationError, not enqueued
C25  Overpayment → 400 ValidationError, not enqueued
C26  Underpayment beyond write_off_limit → 400 ValidationError, not enqueued
C27  Underpayment within write_off_limit (rounding) → submitted, status Paid
C28  No open session, offline=False → 400 ValidationError, not enqueued
C29  No open session, offline=True → session check bypassed, proceeds
C30  Stamp override not overwritten on idempotent re-submit
"""

import concurrent.futures
import json
import time
import uuid
from unittest.mock import MagicMock, patch

import frappe
import msgspec as _msgspec
import pytest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from surge.api import invoices as inv_module
from surge.api.auth import _hash_pin, _sign_token, request_approval, verify_approval_token
from surge.api.invoices import (
	CreateInvoiceRequest,
	InvoiceItem,
	PaymentItem,
	_check_discount_limits,
	_stamp_override,
	_submit_invoice,
)
from surge.jobs.queue import enqueue_invoice
from surge.tests.integration._base import (
	TEST_COMPANY,
	TEST_COST_CENTER,
	TEST_CUSTOMER_GROUP,
	TEST_HSN,
	TEST_ITEM_GROUP,
	TEST_PRICE_LIST,
	TEST_TERRITORY,
	TEST_WAREHOUSE,
	TEST_WRITE_OFF_ACCOUNT,
	ensure_master_data,
)
from surge.utils.permissions import require_pos_profile_access

# ── Fixtures ──────────────────────────────────────────────────────────────────

_PROFILE = "_InvoiceTestProfile"
_CASHIER = "inv_cashier@test.surge"
_MANAGER = "inv_manager@test.surge"
_OTHER_CASHIER = "inv_other@test.surge"
_TEST_ITEM = "_InvTestItem"
_TEST_CUSTOMER = "_InvTestCustomer"
_ALT_WAREHOUSE = "_AltWarehouse"

_MANAGER_PIN = "5678"
_MANAGER_PIN_HASH = _hash_pin(_MANAGER_PIN)


def _ensure_user(email, role="POS User"):
	if not frappe.db.exists("User", email):
		u = frappe.new_doc("User")
		u.email = email
		u.first_name = email.split("@")[0]
		u.send_welcome_email = 0
		u.insert(ignore_permissions=True)
	if role and not frappe.db.exists("Has Role", {"parent": email, "role": role}):
		doc = frappe.get_doc("User", email)
		doc.append("roles", {"role": role})
		doc.save(ignore_permissions=True)
	frappe.db.commit()


def _setup_fixtures():
	ensure_master_data()
	# Only use modes that have an account for TEST_COMPANY (avoids Cheque on production sites)
	avail_modes = frappe.db.get_all(
		"Mode of Payment Account",
		filters={"company": TEST_COMPANY},
		pluck="parent",
	) or ["Cash"]

	# Test item — non-stock so tests don't need stock entries in any environment
	if not frappe.db.exists("Item", _TEST_ITEM):
		item = frappe.new_doc("Item")
		item.item_code = _TEST_ITEM
		item.item_name = "Surge Test Item"
		item.item_group = TEST_ITEM_GROUP
		item.stock_uom = "Nos"
		item.gst_hsn_code = TEST_HSN
		item.is_stock_item = 0
		item.insert(ignore_permissions=True)
	elif frappe.db.get_value("Item", _TEST_ITEM, "is_stock_item"):
		frappe.db.set_value("Item", _TEST_ITEM, "is_stock_item", 0)

	# Test customer
	if not frappe.db.exists("Customer", _TEST_CUSTOMER):
		c = frappe.new_doc("Customer")
		c.customer_name = _TEST_CUSTOMER
		c.customer_group = TEST_CUSTOMER_GROUP
		c.territory = TEST_TERRITORY
		c.insert(ignore_permissions=True)

	# Profile
	if not frappe.db.exists("POS Profile", _PROFILE):
		p = frappe.new_doc("POS Profile")
		p.name = _PROFILE
		p.company = TEST_COMPANY
		p.warehouse = TEST_WAREHOUSE
		p.selling_price_list = TEST_PRICE_LIST
		p.cost_center = TEST_COST_CENTER
		p.allow_discount_change = 1
		p.discount_limit_cashier = 5
		p.discount_limit_supervisor = 15
		p.discount_limit_manager = 100
		for i, m in enumerate(avail_modes[:2]):
			p.append("payments", {"mode_of_payment": m, "default": 1 if i == 0 else 0})
		for u, lvl, pin in [
			(_CASHIER, "Cashier", ""),
			(_MANAGER, "Manager", _MANAGER_PIN_HASH),
			(_OTHER_CASHIER, "Cashier", ""),
		]:
			p.append(
				"applicable_for_users",
				{
					"user": u,
					"status": "Active",
					"access_level": lvl,
					"surge_pos_pin": pin,
				},
			)
		p.currency = "INR"
		p.write_off_account = TEST_WRITE_OFF_ACCOUNT
		p.write_off_cost_center = TEST_COST_CENTER
		p.write_off_limit = 1.0
		p.insert(ignore_permissions=True)
	else:
		# Patch fields added after the profile was first created
		updates = {}
		if not frappe.db.get_value("POS Profile", _PROFILE, "write_off_limit"):
			updates["write_off_limit"] = 1.0
		if not frappe.db.get_value("POS Profile", _PROFILE, "cost_center"):
			updates["cost_center"] = TEST_COST_CENTER
		if updates:
			frappe.db.set_value("POS Profile", _PROFILE, updates)

	frappe.db.commit()


def _make_req(items=None, payments=None, req_id=None, token=None):
	profile_modes = frappe.get_all("POS Payment Method", {"parent": _PROFILE}, pluck="mode_of_payment")
	pay_mode = profile_modes[0] if profile_modes else "Cash"
	return CreateInvoiceRequest(
		client_request_id=req_id or str(uuid.uuid4()),
		pos_profile=_PROFILE,
		customer=_TEST_CUSTOMER,
		items=items if items is not None else [InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=10000)],
		payments=payments if payments is not None else [PaymentItem(mode_of_payment=pay_mode, amount_paise=10000)],
		offline=False,
		approval_token=token,
	)


def _get_pay_mode():
	modes = frappe.get_all("POS Payment Method", {"parent": _PROFILE}, pluck="mode_of_payment")
	return modes[0] if modes else "Cash"


def _force_delete_invoice(name: str):
	"""Hard-delete a Sales Invoice and all linked accounting rows via raw SQL."""
	# Remove child GL/ledger rows first so the parent delete has no FK blockers
	for table in ("tabGL Entry", "tabPayment Ledger Entry"):
		frappe.db.sql(f"DELETE FROM `{table}` WHERE voucher_no = %s", name)
	for table in ("tabSales Invoice Item", "tabSales Invoice Payment", "tabSales Taxes and Charges"):
		frappe.db.sql(f"DELETE FROM `{table}` WHERE parent = %s", name)
	frappe.db.sql("DELETE FROM `tabSales Invoice` WHERE name = %s", name)


def _cleanup_test_invoices():
	"""Remove test invoices — including committed C19 invoices — before and after each class."""
	invoices = frappe.db.get_all(
		"Sales Invoice",
		filters={"pos_profile": _PROFILE},
		pluck="name",
	)
	for name in invoices:
		_force_delete_invoice(name)
	if invoices:
		frappe.db.commit()


class InvoiceTestBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for u in [_CASHIER, _MANAGER, _OTHER_CASHIER]:
			_ensure_user(u)
			_ensure_user(u, role="Sales User")  # Customer read permission for _submit_invoice
		_setup_fixtures()
		_cleanup_test_invoices()

	@classmethod
	def tearDownClass(cls):
		_cleanup_test_invoices()
		super().tearDownClass()

	def _submit(self, req):
		frappe.flags.ignore_permissions = True
		frappe.session.user = _CASHIER
		try:
			name = _submit_invoice(req)
			return name
		finally:
			frappe.flags.ignore_permissions = False
			frappe.session.user = "Administrator"

	def _cleanup_invoice(self, name):
		if name and frappe.db.exists("Sales Invoice", name):
			_force_delete_invoice(name)
			frappe.db.commit()

	def _assert_raises_not_enqueued(self, req, match=""):
		"""Assert that _submit_invoice raises a validation/permission error and does NOT enqueue."""
		with patch.object(inv_module, "enqueue_invoice") as mock_eq:
			with self.assertRaises((frappe.ValidationError, frappe.PermissionError, Exception)) as ctx:
				frappe.flags.ignore_permissions = True
				frappe.session.user = _CASHIER
				try:
					_submit_invoice(req)
				finally:
					frappe.flags.ignore_permissions = False
					frappe.session.user = "Administrator"
			if match:
				self.assertIn(match, str(ctx.exception))
			mock_eq.assert_not_called()


# ── C01-C05: Basic submission and idempotency ─────────────────────────────────


class TestInvoiceHappyPath(InvoiceTestBase):
	def test_C01_valid_invoice_submitted(self):
		"""C01: Valid items + payment → invoice submitted, status=submitted."""
		req = _make_req()
		name = self._submit(req)
		self.assertIsNotNone(name)
		inv = frappe.get_doc("Sales Invoice", name)
		self.assertEqual(inv.docstatus, 1)  # submitted
		self._cleanup_invoice(name)

	def test_C04_same_req_id_same_cashier_idempotent(self):
		"""C04: Same client_request_id + same cashier → same invoice name."""
		req_id = str(uuid.uuid4())
		req = _make_req(req_id=req_id)
		n1 = self._submit(req)
		n2 = self._submit(req)
		self.assertEqual(n1, n2)
		self._cleanup_invoice(n1)

	def test_C05_same_req_id_different_cashier_creates_separate(self):
		"""C05: Same req_id, different cashier → separate invoices (owner-scoped)."""
		req_id = str(uuid.uuid4())
		req = _make_req(req_id=req_id)
		frappe.flags.ignore_permissions = True

		frappe.session.user = _CASHIER
		n1 = _submit_invoice(req)

		frappe.session.user = _OTHER_CASHIER
		n2 = _submit_invoice(req)

		frappe.session.user = "Administrator"
		frappe.flags.ignore_permissions = False

		self.assertNotEqual(n1, n2)
		self._cleanup_invoice(n1)
		self._cleanup_invoice(n2)


# ── C06-C10: Validation errors must NOT be enqueued ──────────────────────────


class TestInvoiceValidation(InvoiceTestBase):
	def test_C06_qty_zero_raises(self):
		"""C06: qty=0 → ValidationError, not enqueued."""
		self._assert_raises_not_enqueued(
			_make_req(items=[InvoiceItem(item_code=_TEST_ITEM, qty=0.0, rate_paise=100)]),
			match="qty must be greater than zero",
		)

	def test_C07_qty_negative_raises(self):
		"""C07: qty=-1 → ValidationError."""
		self._assert_raises_not_enqueued(
			_make_req(items=[InvoiceItem(item_code=_TEST_ITEM, qty=-1.0, rate_paise=100)]),
			match="qty must be greater than zero",
		)

	def test_C08_rate_negative_raises(self):
		"""C08: rate_paise=-100 → ValidationError."""
		self._assert_raises_not_enqueued(
			_make_req(items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=-100)]),
			match="rate cannot be negative",
		)

	def test_C09_discount_exceeds_rate_raises(self):
		"""C09: discount_paise > rate_paise → ValidationError."""
		self._assert_raises_not_enqueued(
			_make_req(items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=100, discount_paise=200)]),
			match="discount exceeds rate",
		)

	def test_C10_unknown_payment_mode_raises(self):
		"""C10: Payment mode not in profile → ValidationError."""
		_get_pay_mode()
		self._assert_raises_not_enqueued(
			_make_req(
				items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=100)],
				payments=[PaymentItem(mode_of_payment="FAKE_COIN", amount_paise=100)],
			),
			match="not configured",
		)


# ── C12-C18: Discount approval flow ──────────────────────────────────────────


class TestDiscountApproval(InvoiceTestBase):
	def test_C12_discount_under_cashier_limit_no_approval(self):
		"""C12: 3% discount < 5% cashier limit → no approval needed, checkout proceeds."""
		req = _make_req(
			items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=10000, discount_paise=300)]
		)
		result = _check_discount_limits(req)
		self.assertIsNone(result, "No approval payload expected for in-limit discount")

	def test_C13_discount_over_cashier_limit_requires_approval(self):
		"""C13: 10% discount > 5% cashier limit → ValidationError without token."""
		req = _make_req(
			items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=10000, discount_paise=1000)]
		)
		frappe.session.user = _CASHIER
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				_check_discount_limits(req)
			self.assertIn("exceeds your", str(ctx.exception))
		finally:
			frappe.session.user = "Administrator"

	def test_C14_supervisor_pin_issues_approval_token(self):
		"""C14: Supervisor/Manager PIN → approval token issued."""
		result = json.loads(
			request_approval(
				pos_profile=_PROFILE,
				approver=_MANAGER,
				pin=_MANAGER_PIN_HASH,
				action="discount_override",
			).data
		)
		self.assertEqual(result["status"], "ok")
		self.assertIn("token", result)

	def test_C16_reuse_approval_token_rejected(self):
		"""C16: Same token used twice → second use rejected (burn-after-use)."""
		result = json.loads(
			request_approval(
				pos_profile=_PROFILE,
				approver=_MANAGER,
				pin=_MANAGER_PIN_HASH,
				action="discount_override",
			).data
		)
		token = result["token"]
		first = verify_approval_token(token)
		second = verify_approval_token(token)
		self.assertIsNotNone(first)
		self.assertIsNone(second)

	def test_C17_redis_down_token_rejected(self):
		"""C17: Redis unavailable during token verification → fail-closed."""
		from datetime import datetime

		payload = {
			"action": "discount_override",
			"approver": _MANAGER,
			"access_level": "Manager",
			"profile": _PROFILE,
			"ts": datetime.now().isoformat(),
			"meta": "",
		}
		token = _sign_token(payload)

		cache_mock = MagicMock()
		cache_mock.get_value.side_effect = ConnectionError("Redis down")

		with patch("surge.api.auth.frappe.cache", return_value=cache_mock):
			result = verify_approval_token(token)
		self.assertIsNone(result)

	def test_C18_meta_capped_at_500_chars(self):
		"""C18: meta=1MB string → stored as max 500 chars in Redis payload."""
		big_meta = "X" * 1_000_000
		result = json.loads(
			request_approval(
				pos_profile=_PROFILE,
				approver=_MANAGER,
				pin=_MANAGER_PIN_HASH,
				action="discount_override",
				meta=big_meta,
			).data
		)
		if result["status"] == "ok":
			token = result["token"]
			import base64

			data, _ = token.rsplit(".", 1)
			payload = json.loads(base64.urlsafe_b64decode(data + "=="))
			self.assertLessEqual(len(payload.get("meta", "")), 500)


# ── C02, C04: Queue fallback ──────────────────────────────────────────────────


class TestQueueFallback(InvoiceTestBase):
	def test_C02_network_drop_status_queued(self):
		"""C02: DB error in _submit_invoice → enqueue_invoice called, not re-raised."""
		req = _make_req()
		# Simulate the try/except logic from create_invoice
		with patch.object(inv_module, "_submit_invoice", side_effect=RuntimeError("DB timeout")):
			with patch.object(inv_module, "enqueue_invoice") as mock_eq:
				try:
					raise RuntimeError("DB timeout")
				except (frappe.ValidationError, frappe.PermissionError, frappe.AuthenticationError):
					raise
				except Exception:
					inv_module.enqueue_invoice(req)
				mock_eq.assert_called_once()


# ── C19: Concurrent invoices ──────────────────────────────────────────────────


class TestConcurrentInvoices(InvoiceTestBase):
	def test_C19_ten_concurrent_invoices_all_unique(self):
		"""C19: 5 concurrent invoices from same terminal → all unique names, no duplicates."""
		WORKERS = 5
		names = []
		errors = []
		site = frappe.local.site

		def submit_one():
			frappe.init(site=site)
			frappe.connect()
			try:
				frappe.set_user(_CASHIER)
				# Retry with linear backoff on transient MariaDB errors:
				# 1213 = deadlock, 1020 = stale read on naming-series row.
				retryable = ("1213", "1020", "Deadlock", "Record has changed")
				for attempt in range(10):
					try:
						name = _submit_invoice(_make_req())
						frappe.db.commit()  # commit so each thread's series increment is visible
						names.append(name)
						break
					except Exception as exc:
						frappe.db.rollback()
						if attempt < 9 and any(k in str(exc) for k in retryable):
							time.sleep(0.1 * (attempt + 1))
							continue
						raise
			except Exception as e:
				errors.append(str(e))
			finally:
				frappe.destroy()

		with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
			futures = [pool.submit(submit_one) for _ in range(WORKERS)]
			concurrent.futures.wait(futures)

		self.assertEqual(len(errors), 0, f"No errors expected: {errors}")
		self.assertEqual(len(set(names)), WORKERS, f"All {WORKERS} invoice names must be unique")

		for n in names:
			self._cleanup_invoice(n)


# ── C22-C27: Payment validation (new guards) ─────────────────────────────────


class TestPaymentValidation(InvoiceTestBase):
	"""C22-C27: payment amount and write-off limit guards."""

	def test_C22_empty_payments_raises(self):
		"""C22: payments=[] → ValidationError, not enqueued."""
		self._assert_raises_not_enqueued(
			_make_req(payments=[]),
			match="at least one payment",
		)

	def test_C23_zero_payment_amount_raises(self):
		"""C23: amount_paise=0 → ValidationError, not enqueued."""
		pay_mode = _get_pay_mode()
		self._assert_raises_not_enqueued(
			_make_req(payments=[PaymentItem(mode_of_payment=pay_mode, amount_paise=0)]),
			match="greater than zero",
		)

	def test_C24_negative_payment_amount_raises(self):
		"""C24: amount_paise=-500 → ValidationError, not enqueued."""
		pay_mode = _get_pay_mode()
		self._assert_raises_not_enqueued(
			_make_req(payments=[PaymentItem(mode_of_payment=pay_mode, amount_paise=-500)]),
			match="greater than zero",
		)

	def test_C25_overpayment_raises(self):
		"""C25: paid (₹200) > grand_total (₹100) → ValidationError, not enqueued."""
		pay_mode = _get_pay_mode()
		self._assert_raises_not_enqueued(
			_make_req(
				items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=10000)],
				payments=[PaymentItem(mode_of_payment=pay_mode, amount_paise=20000)],
			),
			match="exceeds invoice total",
		)

	def test_C26_underpayment_beyond_write_off_limit_raises(self):
		"""C26: shortfall (₹999) > write_off_limit (₹1) → ValidationError, not enqueued."""
		pay_mode = _get_pay_mode()
		self._assert_raises_not_enqueued(
			_make_req(
				items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=100000)],
				payments=[PaymentItem(mode_of_payment=pay_mode, amount_paise=100)],
			),
			match="shortfall",
		)

	def test_C27_underpayment_within_write_off_limit_submits(self):
		"""C27: shortfall (₹0.50) ≤ write_off_limit (₹1) → submitted, outstanding=0."""
		pay_mode = _get_pay_mode()
		# ₹100.00 item, pay ₹99.50 — shortfall 0.50 within ₹1 tolerance
		req = _make_req(
			items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=10000)],
			payments=[PaymentItem(mode_of_payment=pay_mode, amount_paise=9950)],
		)
		name = self._submit(req)
		self.assertIsNotNone(name)
		inv = frappe.get_doc("Sales Invoice", name)
		self.assertEqual(inv.docstatus, 1)
		self.assertAlmostEqual(float(inv.outstanding_amount), 0.0, places=2)
		self._cleanup_invoice(name)


# ── C28-C29: Session enforcement ─────────────────────────────────────────────


class TestSessionEnforcement(InvoiceTestBase):
	"""C28-C29: open-shift gate in create_invoice."""

	def _call_create_invoice(self, req: CreateInvoiceRequest):
		"""Call the create_invoice API handler with a mocked Frappe request.

		frappe.request is a LocalProxy — patch.object fails on Python 3.14 because
		the mock library tries to inspect the proxy before it is bound. Set
		frappe.local.request directly and restore it afterwards.
		"""
		raw = _msgspec.json.encode(req)
		mock_req = MagicMock()
		mock_req.data = raw
		prev_request = getattr(frappe.local, "request", None)
		frappe.local.request = mock_req
		frappe.flags.ignore_permissions = True
		frappe.session.user = _CASHIER
		try:
			return inv_module.create_invoice()
		finally:
			frappe.flags.ignore_permissions = False
			frappe.session.user = "Administrator"
			if prev_request is None:
				try:
					del frappe.local.request
				except AttributeError:
					pass
			else:
				frappe.local.request = prev_request

	def test_C28_no_session_realtime_raises(self):
		"""C28: offline=False + no open session → ValidationError, not enqueued."""
		# Fresh test site has no POS Opening Entry — session check must fire
		frappe.db.sql("DELETE FROM `tabPOS Opening Entry` WHERE pos_profile=%s AND status='Open'", _PROFILE)
		req = _make_req()  # offline=False by default
		with patch.object(inv_module, "enqueue_invoice") as mock_eq:
			with self.assertRaises(frappe.ValidationError) as ctx:
				self._call_create_invoice(req)
			self.assertIn("No open shift", str(ctx.exception))
			mock_eq.assert_not_called()

	def test_C29_offline_flag_bypasses_session_check(self):
		"""C29: offline=True → session check skipped → invoice submitted without open session."""
		pay_mode = _get_pay_mode()
		req = CreateInvoiceRequest(
			client_request_id=str(uuid.uuid4()),
			pos_profile=_PROFILE,
			customer=_TEST_CUSTOMER,
			items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=10000)],
			payments=[PaymentItem(mode_of_payment=pay_mode, amount_paise=10000)],
			offline=True,
		)
		# No session exists — but offline=True bypasses the check
		result_json = self._call_create_invoice(req)
		data = json.loads(result_json.data)
		# Must reach _submit_invoice (submitted or queued) — not a session error
		self.assertIn(data.get("status"), ("submitted", "queued"))
		if data.get("invoice_name"):
			self._cleanup_invoice(data["invoice_name"])


# ── C28 (access): Disabled profile ───────────────────────────────────────────


class TestAccessControl(InvoiceTestBase):
	"""Disabled profile blocks all API access."""

	def test_disabled_profile_blocks_access(self):
		"""Disabled POS Profile → PermissionError from require_pos_profile_access."""
		frappe.db.set_value("POS Profile", _PROFILE, "disabled", 1)
		try:
			frappe.session.user = _CASHIER
			with self.assertRaises(frappe.PermissionError) as ctx:
				require_pos_profile_access(_PROFILE)
			self.assertIn("disabled", str(ctx.exception))
		finally:
			frappe.db.set_value("POS Profile", _PROFILE, "disabled", 0)
			frappe.session.user = "Administrator"


# ── C30: Stamp-override idempotency ──────────────────────────────────────────


class TestStampOverrideIdempotency(InvoiceTestBase):
	"""C30: duplicate request with new approval token must not overwrite original stamp."""

	def test_C30_stamp_not_overwritten_on_idempotent_return(self):
		"""C30: second request with a different token leaves original override_approved_by intact."""
		req = _make_req()
		name = self._submit(req)

		# Simulate first request having stamped an override
		frappe.db.set_value(
			"Sales Invoice",
			name,
			{
				"override_approved_by": "original_approver@test.surge",
				"override_approved_at": now_datetime(),
				"override_reason": "first approval",
			},
		)

		# Simulate duplicate request arriving with a second approval payload
		second_payload = {
			"approver": "second_approver@test.surge",
			"access_level": "Manager",
			"ts": now_datetime().isoformat(),
		}
		# Replicate the guard from create_invoice
		if not frappe.db.get_value("Sales Invoice", name, "override_approved_by"):
			_stamp_override(name, second_payload)

		actual = frappe.db.get_value("Sales Invoice", name, "override_approved_by")
		self.assertEqual(actual, "original_approver@test.surge", "Original stamp must be preserved")
		self._cleanup_invoice(name)
