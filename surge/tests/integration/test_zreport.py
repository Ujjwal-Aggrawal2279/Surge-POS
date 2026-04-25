"""
Integration tests — Group F (Z-Report Accuracy) — Scenarios F01–F10.

F01  net_sales_paise = sum(grand_total for non-returns) × 100
F02  net_returns_paise = sum(grand_total for is_return) × 100
F03  per-mode payment amounts summed correctly
F04  discrepancy negative when cashier is short
F05  discrepancy formula: actual - (opening + sales)
F06  ₹10.10 → 1010 paise (no float drift)
F07  extra closing mode not in opening → appears in Z-report
F08  midnight crossing: period_start yesterday → today's invoices included
F09  zero-invoice shift → all paise values = 0
F10  returns-only session → net_sales=0, net_returns>0
"""
import uuid
from datetime import timedelta
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, nowdate

from surge.api.session import _build_z_report

_PROFILE = "_ZReportProfile"


def _get_company():
    return frappe.db.get_single_value("Global Defaults", "default_company")


def _make_entry(balance_details=None, period_start=None):
    return SimpleNamespace(
        name=f"TEST-ZOPEN-{uuid.uuid4().hex[:6].upper()}",
        pos_profile=_PROFILE,
        period_start_date=period_start or now_datetime(),
        user="zreport@test.surge",
        balance_details=[
            SimpleNamespace(mode_of_payment=k, opening_amount=v)
            for k, v in (balance_details or {}).items()
        ],
    )


def _insert_invoice(grand_total, is_return=0, modes=None, posting_date=None, tax=0.0):
    name = f"TEST-ZINV-{uuid.uuid4().hex[:8].upper()}"
    company = _get_company()
    ts = now_datetime()
    frappe.db.sql(
        """INSERT INTO `tabSales Invoice`
           (name, creation, modified, modified_by, owner, docstatus,
            is_pos, pos_profile, company, customer, currency,
            grand_total, base_grand_total, net_total,
            total_taxes_and_charges, is_return, posting_date, outstanding_amount)
           VALUES (%s, %s, %s, 'Administrator', 'Administrator', 1,
                   1, %s, %s, 'Guest', 'INR',
                   %s, %s, %s,
                   %s, %s, %s, 0)""",
        (name, ts, ts, _PROFILE, company,
         grand_total, grand_total, grand_total - tax,
         tax, is_return, posting_date or nowdate()),
    )
    for mode, amount in (modes or {}).items():
        row_name = frappe.generate_hash(length=10)
        frappe.db.sql(
            """INSERT INTO `tabSales Invoice Payment`
               (name, creation, modified, modified_by, owner, docstatus,
                parent, parentfield, parenttype, mode_of_payment, amount)
               VALUES (%s, %s, %s, 'Administrator', 'Administrator', 1,
                       %s, 'payments', 'Sales Invoice', %s, %s)""",
            (row_name, ts, ts, name, mode, amount),
        )
    frappe.db.commit()
    return name


def _clean_test_invoices():
    frappe.db.sql(
        """DELETE sip FROM `tabSales Invoice Payment` sip
           INNER JOIN `tabSales Invoice` si ON si.name = sip.parent
           WHERE si.pos_profile = %s AND si.name LIKE 'TEST-ZINV-%%'""",
        (_PROFILE,),
    )
    frappe.db.sql(
        "DELETE FROM `tabSales Invoice` WHERE pos_profile = %s AND name LIKE 'TEST-ZINV-%%'",
        (_PROFILE,),
    )
    frappe.db.commit()


class ZReportBase(FrappeTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not frappe.db.exists("POS Profile", _PROFILE):
            company = _get_company()
            wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")
            p = frappe.new_doc("POS Profile")
            p.name = _PROFILE
            p.company = company
            p.warehouse = wh
            p.selling_price_list = frappe.db.get_value("Price List", {"buying": 0}, "name")
            for m in frappe.get_all("Mode of Payment", limit=2, pluck="name"):
                p.append("payments", {"mode_of_payment": m})
            p.insert(ignore_permissions=True)
            frappe.db.commit()

    def setUp(self):
        _clean_test_invoices()

    def tearDown(self):
        _clean_test_invoices()


class TestZReportMath(ZReportBase):

    def test_F01_net_sales_paise_correct(self):
        """F01: 2 invoices ₹100 each → net_sales_paise = 20000."""
        _insert_invoice(100.0)
        _insert_invoice(100.0)
        report = _build_z_report(_make_entry(), [], "")
        self.assertEqual(report["net_sales_paise"], 20000)
        self.assertEqual(report["total_invoices"], 2)

    def test_F02_net_returns_paise_correct(self):
        """F02: 1 return invoice ₹50 → net_returns_paise = 5000, net_sales = 0."""
        _insert_invoice(50.0, is_return=1)
        report = _build_z_report(_make_entry(), [], "")
        self.assertEqual(report["net_returns_paise"], 5000)
        self.assertEqual(report["net_sales_paise"], 0)
        self.assertEqual(report["total_returns"], 1)
        self.assertEqual(report["total_invoices"], 0)

    def test_F03_per_mode_amounts_summed(self):
        """F03: Cash ₹60 + Card ₹40 → mode breakdown reflects those amounts."""
        _insert_invoice(100.0, modes={"Cash": 60.0, "Card": 40.0})
        report = _build_z_report(_make_entry(balance_details={"Cash": 0.0}),
                                 [{"mode_of_payment": "Cash", "amount": 60.0}], "")
        mode_map = {m["mode_of_payment"]: m for m in report["payment_modes"]}
        self.assertIn("Cash", mode_map)
        self.assertEqual(mode_map["Cash"]["sales_amount_paise"], 6000)

    def test_F04_discrepancy_negative_when_short(self):
        """F04: Closing ₹90 vs expected ₹100 → discrepancy_paise = -1000."""
        _insert_invoice(100.0, modes={"Cash": 100.0})
        closing = [{"mode_of_payment": "Cash", "amount": 90.0}]
        report = _build_z_report(_make_entry(balance_details={"Cash": 0.0}), closing, "short")
        mode = next(m for m in report["payment_modes"] if m["mode_of_payment"] == "Cash")
        self.assertEqual(mode["discrepancy_paise"], -1000)

    def test_F05_discrepancy_formula_opening_plus_sales(self):
        """F05: opening ₹50 + sales ₹100 = expected ₹150; actual ₹160 → +1000 paise."""
        _insert_invoice(100.0, modes={"Cash": 100.0})
        closing = [{"mode_of_payment": "Cash", "amount": 160.0}]
        report = _build_z_report(_make_entry(balance_details={"Cash": 50.0}), closing, "")
        mode = next(m for m in report["payment_modes"] if m["mode_of_payment"] == "Cash")
        self.assertEqual(mode["expected_amount_paise"], 15000)
        self.assertEqual(mode["discrepancy_paise"], 1000)

    def test_F06_paise_precision_no_float_drift(self):
        """F06: ₹10.10 → 1010 paise, no IEEE 754 drift (10.10 * 100 = 1009.9999... in raw float)."""
        _insert_invoice(10.10)
        report = _build_z_report(_make_entry(), [], "")
        self.assertEqual(report["net_sales_paise"], 1010)

    def test_F07_extra_closing_mode_appears_in_report(self):
        """F07: Closing includes 'Cheque' not in opening → union includes both modes."""
        closing = [
            {"mode_of_payment": "Cash", "amount": 100.0},
            {"mode_of_payment": "Cheque", "amount": 50.0},
        ]
        report = _build_z_report(_make_entry(balance_details={"Cash": 100.0}), closing, "")
        modes = {m["mode_of_payment"] for m in report["payment_modes"]}
        self.assertIn("Cash", modes)
        self.assertIn("Cheque", modes)

    def test_F08_midnight_crossing_includes_todays_invoices(self):
        """F08: Session opened yesterday → today's invoices (nowdate) are included."""
        yesterday = now_datetime() - timedelta(days=1)
        _insert_invoice(200.0)  # posting_date = nowdate() (today)
        report = _build_z_report(_make_entry(period_start=yesterday), [], "")
        self.assertEqual(report["net_sales_paise"], 20000)

    def test_F09_zero_invoice_shift_all_zeros(self):
        """F09: No invoices for profile → all sales/returns/tax paise = 0."""
        report = _build_z_report(
            _make_entry(balance_details={"Cash": 100.0}),
            [{"mode_of_payment": "Cash", "amount": 100.0}],
            "",
        )
        self.assertEqual(report["net_sales_paise"], 0)
        self.assertEqual(report["net_returns_paise"], 0)
        self.assertEqual(report["total_tax_paise"], 0)
        self.assertEqual(report["total_invoices"], 0)

    def test_F10_returns_only_session(self):
        """F10: Only return invoices → net_sales=0, net_returns>0, total_returns=1."""
        _insert_invoice(75.0, is_return=1)
        report = _build_z_report(_make_entry(), [], "")
        self.assertEqual(report["net_sales_paise"], 0)
        self.assertEqual(report["net_returns_paise"], 7500)
        self.assertEqual(report["total_returns"], 1)
        self.assertEqual(report["total_invoices"], 0)
