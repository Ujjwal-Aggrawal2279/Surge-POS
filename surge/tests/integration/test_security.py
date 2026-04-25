"""
Integration tests — Group H (Security Edge Cases) — Scenarios H01–H08.

Cross-reference: several H scenarios are already covered in other files.
H01  meta=1MB capped → test_invoices.py::TestDiscountApproval::test_C18
H02  FAKE_COIN payment mode → test_invoices.py::TestInvoiceValidation::test_C10
H04  token replay → test_invoices.py::TestDiscountApproval::test_C16
H05  Redis fail-closed → test_invoices.py::TestDiscountApproval::test_C17
H06  forgot_pin rate limit → test_auth.py::TestPINLogin::test_A09

New scenarios in this file:
H03  Nonexistent customer → invoice creation raises
H07  HMAC secret unavailable → _sign_token raises
H08  Non-POS Sales Invoice on_submit → early return, no audit log written
"""
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from surge.api.auth import _sign_token
from surge.api.invoices import (
    CreateInvoiceRequest,
    InvoiceItem,
    PaymentItem,
    _submit_invoice,
)
from surge.overrides.sales_invoice import on_submit as inv_on_submit


_PROFILE = "_HSecProfile"
_CASHIER = "h_cashier@test.surge"
_TEST_ITEM = "_HSecItem"


def _ensure_user(email):
    if not frappe.db.exists("User", email):
        u = frappe.new_doc("User")
        u.email = email
        u.first_name = email.split("@")[0]
        u.send_welcome_email = 0
        u.insert(ignore_permissions=True)
        frappe.db.commit()


def _setup():
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")

    if not frappe.db.exists("Item", _TEST_ITEM):
        item = frappe.new_doc("Item")
        item.item_code = _TEST_ITEM
        item.item_name = "Surge Security Test Item"
        item.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        item.stock_uom = "Nos"
        item.is_stock_item = 1
        item.insert(ignore_permissions=True)

    if not frappe.db.exists("POS Profile", _PROFILE):
        modes = frappe.get_all("Mode of Payment", limit=1, pluck="name")
        p = frappe.new_doc("POS Profile")
        p.name = _PROFILE
        p.company = company
        p.warehouse = wh
        p.selling_price_list = frappe.db.get_value("Price List", {"buying": 0}, "name")
        for m in modes:
            p.append("payments", {"mode_of_payment": m})
        p.append("applicable_for_users", {
            "user": _CASHIER, "status": "Active", "access_level": "Cashier",
        })
        p.insert(ignore_permissions=True)

    frappe.db.commit()
    return frappe.get_all("POS Profile Payments", {"parent": _PROFILE}, pluck="mode_of_payment")[0]


class TestSecurityEdgeCases(FrappeTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_user(_CASHIER)
        cls._pay_mode = _setup()

    # ── H03: Nonexistent customer ─────────────────────────────────────────────

    def test_H03_nonexistent_customer_raises(self):
        """H03: Customer='DOES_NOT_EXIST_XYZ' → invoice.insert() raises before submission."""
        req = CreateInvoiceRequest(
            client_request_id="h03-test",
            pos_profile=_PROFILE,
            customer="DOES_NOT_EXIST_XYZ_99999",
            items=[InvoiceItem(item_code=_TEST_ITEM, qty=1.0, rate_paise=1000)],
            payments=[PaymentItem(mode_of_payment=self._pay_mode, amount_paise=1000)],
            offline=False,
        )
        frappe.flags.ignore_permissions = True
        frappe.session.user = _CASHIER
        try:
            with self.assertRaises(Exception):
                _submit_invoice(req)
        finally:
            frappe.flags.ignore_permissions = False
            frappe.session.user = "Administrator"

    # ── H07: HMAC secret unavailable ─────────────────────────────────────────

    def test_H07_hmac_secret_unavailable_raises(self):
        """H07: get_encryption_key raises → _sign_token propagates the error."""
        payload = {
            "action": "discount_override",
            "approver": "manager@test.com",
            "access_level": "Manager",
            "profile": _PROFILE,
            "ts": "2026-01-01T00:00:00",
            "meta": "",
        }
        with patch(
            "surge.api.auth._get_hmac_secret",
            side_effect=RuntimeError("Encryption key unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                _sign_token(payload)

    # ── H08: Non-POS invoice on_submit → early return ─────────────────────────

    def test_H08_non_pos_invoice_on_submit_early_return(self):
        """H08: is_pos=0 → on_submit returns without writing audit log or realtime event."""
        doc = MagicMock()
        doc.is_pos = 0
        doc.name = "NONPOS-INV-001"
        doc.pos_profile = ""
        doc.owner = "Administrator"
        doc.grand_total = 500.0
        doc.get.return_value = ""

        # on_submit must return without touching the audit log
        with patch("surge.overrides.sales_invoice.frappe") as mock_frappe:
            mock_frappe.db.table_exists.return_value = True
            inv_on_submit(doc)
            # Neither new_doc nor publish_realtime should be called for a non-POS invoice
            mock_frappe.new_doc.assert_not_called()
            mock_frappe.publish_realtime.assert_not_called()
