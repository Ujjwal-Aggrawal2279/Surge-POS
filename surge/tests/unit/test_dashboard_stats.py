"""
Unit tests — Group G (Dashboard Stats) — G01-G22.

No Frappe site required.  Every frappe DB / cache call is mocked with
controlled return values.  Tests verify SQL content, aggregation logic,
response shape, and the manager permission gate.

Run with:
    pytest apps/surge/surge/tests/unit/test_dashboard_stats.py -v

Or via bench (bench initialises the site but tests never touch the DB):
    bench --site <site> run-tests --app surge \
          --module surge.tests.unit.test_dashboard_stats
"""

import re
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import orjson

# ── Constants ────────────────────────────────────────────────────────────────

_COMPANY = "_TestSurgeCo"
_FROM = "2026-01-01"
_TO = "2026-01-31"


# ── Row constructors (match the SimpleNamespace attribute names dashboard.py
#    accesses on each query result) ───────────────────────────────────────────


def _si(total_sales=0.0, total_returns=0.0, invoice_count=0, outstanding=0.0):
	return SimpleNamespace(
		total_sales=total_sales,
		total_returns=total_returns,
		invoice_count=invoice_count,
		outstanding=outstanding,
	)


def _pr(total_purchase=0.0, purchase_returns=0.0):
	return SimpleNamespace(total_purchase=total_purchase, purchase_returns=purchase_returns)


def _exp(expenses=0.0):
	return SimpleNamespace(expenses=expenses)



# ── Mock factory ─────────────────────────────────────────────────────────────


class _FrappePermissionError(Exception):
	"""Stand-in for frappe.PermissionError — raised by mock_throw below."""


def _make_frappe(
	*,
	is_manager: bool = True,
	si_row=None,
	pr_row=None,
	exp_row=None,
	currency_code: str = "INR",
	currency_symbol: str = "₹",
) -> MagicMock:
	"""
	Build a MagicMock for the `frappe` module used inside dashboard.py.

	get_dashboard_stats now makes exactly 3 SQL calls:
	    1. Sales Invoice KPI  → [si_row]
	    2. Purchase Receipt   → [pr_row]
	    3. GL Entry expenses  → [exp_row]

	Overview counts, recent transactions, top products, and low stock are
	served by dedicated endpoints (get_overall_info, get_widgets_data, etc.)
	and are no longer part of get_dashboard_stats.
	"""
	m = MagicMock()

	# ── Manager gate ─────────────────────────────────────────────────────────
	m.db.exists.return_value = is_manager
	m.PermissionError = _FrappePermissionError

	def _throw(msg, exc=Exception):
		raise exc(msg)

	m.throw.side_effect = _throw
	m.session = SimpleNamespace(user="mgr@test.surge")

	# ── Company resolution ────────────────────────────────────────────────────
	m.defaults.get_user_default.return_value = _COMPANY
	m.db.get_single_value.return_value = _COMPANY

	# ── Cache: always miss so the function runs the full SQL path ─────────────
	_cache = MagicMock()
	_cache.get_value.return_value = None
	m.cache.return_value = _cache

	# ── SQL side-effects (3 calls: SI KPI, Purchase, GL expenses) ────────────
	m.db.sql.side_effect = [
		[si_row if si_row is not None else _si()],
		[pr_row if pr_row is not None else _pr()],
		[exp_row if exp_row is not None else _exp()],
	]

	# ── Currency (two get_value calls) ───────────────────────────────────────
	m.db.get_value.side_effect = [currency_code, currency_symbol]

	return m


# ── Test runner ───────────────────────────────────────────────────────────────


def _call(mock_frappe, from_date: str = _FROM, to_date: str = _TO) -> dict:
	"""
	Invoke get_dashboard_stats under a fully mocked frappe and return the
	parsed response dict.  surge_response is NOT mocked — we use the real
	werkzeug Response and decode it with orjson.
	"""
	from surge.api.dashboard import get_dashboard_stats

	with patch("surge.api.dashboard.frappe", mock_frappe):
		resp = get_dashboard_stats(from_date=from_date, to_date=to_date)
	return orjson.loads(resp.get_data())


# ── Helper: get ordered SQL query strings from mock ───────────────────────────


def _sql_calls(mock_frappe) -> list[str]:
	return [str(c.args[0]) for c in mock_frappe.db.sql.call_args_list]


# ── G01-G09: KPI values and SQL filter correctness ───────────────────────────


class TestKPIValues(unittest.TestCase):
	def test_G01_empty_data_all_zeros(self):
		"""G01: All SQL rows return 0 → every KPI field is 0."""
		data = _call(_make_frappe())
		kpi = data["kpi"]
		self.assertEqual(kpi["total_sales"], 0.0)
		self.assertEqual(kpi["total_returns"], 0.0)
		self.assertEqual(kpi["invoice_count"], 0)
		self.assertEqual(kpi["outstanding"], 0.0)
		self.assertEqual(kpi["profit"], 0.0)
		self.assertEqual(kpi["expenses"], 0.0)

	def test_G02_total_sales_from_si_row(self):
		"""G02: total_sales in response equals what the SQL row returns."""
		data = _call(_make_frappe(si_row=_si(total_sales=4230.0, invoice_count=3)))
		self.assertEqual(data["kpi"]["total_sales"], 4230.0)
		self.assertEqual(data["kpi"]["invoice_count"], 3)

	def test_G03_total_returns_from_si_row(self):
		"""G03: total_returns reflects is_return=1 sales — separate from total_sales."""
		data = _call(_make_frappe(si_row=_si(total_sales=1000.0, total_returns=200.0)))
		self.assertEqual(data["kpi"]["total_sales"], 1000.0)
		self.assertEqual(data["kpi"]["total_returns"], 200.0)

	def test_G04_profit_is_pos_sales_minus_purchase(self):
		"""G04: profit = POS total_sales - total_purchase (COGS approximation)."""
		data = _call(
			_make_frappe(
				si_row=_si(total_sales=5000.0),
				pr_row=_pr(total_purchase=3200.0),
			)
		)
		self.assertAlmostEqual(data["kpi"]["profit"], 1800.0, places=2)

	def test_G05_non_pos_purchase_does_not_inflate_profit(self):
		"""G05: purchase_returns from Purchase Receipt do not affect profit formula."""
		data = _call(
			_make_frappe(
				si_row=_si(total_sales=1000.0),
				pr_row=_pr(total_purchase=400.0, purchase_returns=100.0),
			)
		)
		# profit = sales(1000) - purchase(400); purchase_returns is tracked
		# separately and not added back into profit in the current formula.
		self.assertAlmostEqual(data["kpi"]["profit"], 600.0, places=2)

	def test_G06_expenses_from_gl_query(self):
		"""G06: expenses KPI comes from GL Entry query, not Sales or Purchase."""
		data = _call(_make_frappe(exp_row=_exp(expenses=74930.0)))
		self.assertAlmostEqual(data["kpi"]["expenses"], 74930.0, places=2)

	def test_G07_outstanding_from_si_row(self):
		"""G07: outstanding (Invoice Due) comes from the POS-filtered SI query."""
		data = _call(_make_frappe(si_row=_si(outstanding=500.0)))
		self.assertAlmostEqual(data["kpi"]["outstanding"], 500.0, places=2)

	def test_G08_currency_symbol_in_response(self):
		"""G08: currency_symbol is taken from the Currency doctype via get_value."""
		data = _call(_make_frappe(currency_symbol="€"))
		self.assertEqual(data["currency_symbol"], "€")

	def test_G09_kpi_has_invoice_count(self):
		"""G09: invoice_count is returned inside the kpi dict (not a top-level overview)."""
		data = _call(_make_frappe(si_row=_si(invoice_count=7)))
		self.assertEqual(data["kpi"]["invoice_count"], 7)


# ── G10-G14: SQL query content — verify is_pos=1 filter is present ───────────


class TestSQLFilters(unittest.TestCase):
	"""
	After calling get_dashboard_stats, inspect the actual SQL strings that were
	passed to frappe.db.sql.  Each query that touches Sales Invoice must contain
	'is_pos' to ensure non-POS desk invoices are excluded.
	"""

	def setUp(self):
		self.mock_frappe = _make_frappe(si_row=_si(total_sales=100.0))
		self.data = _call(self.mock_frappe)
		self.sql_calls = _sql_calls(self.mock_frappe)

	def test_G10_sales_kpi_query_has_is_pos_filter(self):
		"""G10: The Sales Invoice KPI query (call #1) includes is_pos."""
		si_sql = self.sql_calls[0]
		self.assertIn("is_pos", si_sql)
		# Confirm it's a positive filter (= 1) not a negative one
		self.assertRegex(si_sql, r"is_pos\s*=\s*1")

	def test_G11_sales_kpi_query_scopes_to_docstatus_1(self):
		"""G11: Sales KPI only counts submitted invoices (docstatus = 1)."""
		si_sql = self.sql_calls[0]
		self.assertIn("docstatus", si_sql)
		self.assertIn("1", si_sql)

	def test_G12_purchase_kpi_query_filters_by_docstatus(self):
		"""G12: Purchase Receipt KPI query (call #2) filters docstatus = 1."""
		pr_sql = self.sql_calls[1]
		self.assertIn("docstatus", pr_sql)
		self.assertRegex(pr_sql, r"docstatus\s*=\s*1")

	def test_G13_expense_query_scopes_to_expense_account_type(self):
		"""G13: GL Entry expense query (call #3) filters by root_type = 'Expense'."""
		exp_sql = self.sql_calls[2]
		self.assertIn("Expense", exp_sql)

	def test_G14_expense_query_excludes_cancelled_entries(self):
		"""G14: GL Entry expense query excludes cancelled entries (is_cancelled = 0)."""
		exp_sql = self.sql_calls[2]
		self.assertIn("is_cancelled", exp_sql)
		self.assertRegex(exp_sql, r"is_cancelled\s*=\s*0")

	def test_G15_sales_kpi_uses_date_range_params(self):
		"""G15: All three money queries receive from_date and to_date via params."""
		params = self.mock_frappe.db.sql.call_args_list[0].args[1]
		self.assertEqual(params["from_date"], _FROM)
		self.assertEqual(params["to_date"], _TO)
		self.assertEqual(params["company"], _COMPANY)


# ── G16-G18: Response shape ───────────────────────────────────────────────────


class TestResponseShape(unittest.TestCase):
	def setUp(self):
		self.data = _call(_make_frappe(
			si_row=_si(total_sales=500.0, invoice_count=3),
			pr_row=_pr(total_purchase=200.0),
		))

	def test_G16_response_has_required_top_level_keys(self):
		"""G16: Response dict contains currency_symbol and kpi.
		(overview/recent/products/low_stock are served by dedicated endpoints.)"""
		for key in ("currency_symbol", "kpi"):
			self.assertIn(key, self.data, f"Missing key: {key}")

	def test_G17_kpi_has_all_fields(self):
		"""G17: kpi dict contains every field the frontend reads."""
		for field in (
			"total_sales",
			"total_returns",
			"total_purchase",
			"purchase_returns",
			"profit",
			"outstanding",
			"expenses",
			"invoice_count",
		):
			self.assertIn(field, self.data["kpi"], f"Missing kpi field: {field}")

	def test_G18_kpi_profit_computed_from_sales_and_purchase(self):
		"""G18: profit in kpi equals total_sales minus total_purchase."""
		self.assertAlmostEqual(self.data["kpi"]["profit"], 300.0, places=2)

	def test_G19_kpi_values_match_mocked_rows(self):
		"""G19: total_sales and invoice_count reflect the mocked SI row values."""
		self.assertEqual(self.data["kpi"]["total_sales"], 500.0)
		self.assertEqual(self.data["kpi"]["invoice_count"], 3)

	def test_G20_currency_symbol_present(self):
		"""G20: currency_symbol is returned at the top level."""
		self.assertEqual(self.data["currency_symbol"], "₹")


# ── G21: Cache behaviour ─────────────────────────────────────────────────────


class TestCacheBehaviour(unittest.TestCase):
	def test_G21_cache_hit_skips_sql(self):
		"""G21: When Redis returns a cached payload, frappe.db.sql is never called."""
		m = _make_frappe()
		# Override the cache mock to simulate a hit
		cached_payload = {
			"currency_symbol": "₹",
			"kpi": {
				"total_sales": 999.0,
				"total_returns": 0.0,
				"total_purchase": 0.0,
				"purchase_returns": 0.0,
				"profit": 999.0,
				"outstanding": 0.0,
				"expenses": 0.0,
				"invoice_count": 1,
			},
			"overview": {"customers": 1, "suppliers": 1, "pos_sessions": 0},
			"recent_transactions": [],
			"top_products": [],
			"low_stock": [],
		}
		m.cache.return_value.get_value.return_value = cached_payload

		data = _call(m)

		m.db.sql.assert_not_called()
		self.assertEqual(data["kpi"]["total_sales"], 999.0)

	def test_G21b_cache_miss_calls_exactly_three_sql_queries(self):
		"""G21b: Cache miss → frappe.db.sql called exactly 3 times (SI, PR, GL)."""
		m = _make_frappe()
		_call(m)
		self.assertEqual(m.db.sql.call_count, 3)

	def test_G21c_result_stored_in_cache_after_computation(self):
		"""G21c: After a cache miss, the computed result is stored via cache.set_value."""
		m = _make_frappe()
		_call(m)
		m.cache.return_value.set_value.assert_called_once()
		# Confirm TTL of 300 seconds
		_, kwargs = m.cache.return_value.set_value.call_args
		self.assertEqual(kwargs.get("expires_in_sec"), 300)


# ── G22: Manager gate ─────────────────────────────────────────────────────────


class TestManagerGate(unittest.TestCase):
	def test_G22_non_manager_raises_permission_error(self):
		"""G22: User not in POS Profile User with Manager/Supervisor → PermissionError."""
		m = _make_frappe(is_manager=False)
		from surge.api.dashboard import get_dashboard_stats

		with patch("surge.api.dashboard.frappe", m):
			with self.assertRaises(_FrappePermissionError):
				get_dashboard_stats(from_date=_FROM, to_date=_TO)

		# Confirm the DB was queried for the user's manager status
		m.db.exists.assert_called_once()
		# And no SQL was executed (permission gate is pre-flight)
		m.db.sql.assert_not_called()


# ── G23: manager_get_list validation ─────────────────────────────────────────


class TestManagerGetList(unittest.TestCase):
	def _make_list_frappe(self, *, is_manager=True):
		m = MagicMock()
		m.db.exists.return_value = is_manager
		m.PermissionError = _FrappePermissionError
		m.ValidationError = type("ValidationError", (Exception,), {})
		m.throw.side_effect = lambda msg, exc=Exception: (_ for _ in ()).throw(exc(msg))
		m.get_list.return_value = []
		return m

	def test_G23a_invalid_fields_json_raises_validation_error(self):
		"""G23a: 'Invalid fields or filters JSON.' - malformed JSON raises ValidationError."""
		from surge.api.dashboard import manager_get_list

		m = self._make_list_frappe()
		with patch("surge.api.dashboard.frappe", m):
			with self.assertRaises(m.ValidationError):
				manager_get_list(doctype="Item", fields="{not-json}")

	def test_G23b_disallowed_doctype_raises_permission_error(self):
		"""G23b: DocType not in allowlist raises PermissionError."""
		from surge.api.dashboard import manager_get_list

		m = self._make_list_frappe()
		with patch("surge.api.dashboard.frappe", m):
			with self.assertRaises(_FrappePermissionError):
				manager_get_list(doctype="User")

	def test_G23c_non_manager_blocked_before_list(self):
		"""G23c: Non-manager cannot call manager_get_list."""
		from surge.api.dashboard import manager_get_list

		m = self._make_list_frappe(is_manager=False)
		with patch("surge.api.dashboard.frappe", m):
			with self.assertRaises(_FrappePermissionError):
				manager_get_list(doctype="Item")

		m.get_list.assert_not_called()


if __name__ == "__main__":
	unittest.main()
