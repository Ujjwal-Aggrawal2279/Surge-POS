"""
Unit tests — Group H/P/R/W — Dashboard widget endpoints.

Covers:
    H01-H07  get_customer_overview  (5 calendar periods, counts, %s)
    P01-P08  get_top_products       (4 periods, SQL fragments, shape)
    R01-R08  get_recent_items       (4 periods, multi-invoice, shape)
    W01-W05  get_widgets_data       (low_stock SQL safety, cache, shape)

No Frappe site required — every frappe call is mocked.

Run:
    pytest apps/surge/surge/tests/unit/test_dashboard_widgets.py -v
"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import orjson

_COMPANY = "_TestSurgeCo"


# ── Row constructors ──────────────────────────────────────────────────────────


def _cust_row(customer_type: str, customer: str = "C1"):
	return SimpleNamespace(customer=customer, customer_type=customer_type)


def _top_row(item_code="BEER-001", item_name="Beer", total_qty=10.0, total_amount=1000.0):
	return SimpleNamespace(
		item_code=item_code,
		item_name=item_name,
		total_qty=total_qty,
		total_amount=total_amount,
	)


def _recent_row(
	item_code="BEER-001",
	item_name="Beer",
	item_group="Spirits",
	rate=250.0,
	qty=2.0,
	invoice="SINV-001",
	posting_date="2026-01-15",
	status="Paid",
):
	return SimpleNamespace(
		item_code=item_code,
		item_name=item_name,
		item_group=item_group,
		rate=rate,
		qty=qty,
		invoice=invoice,
		posting_date=posting_date,
		status=status,
	)


def _low_row(
	item_code="BEER-001",
	item_name="Beer",
	warehouse="Stores",
	actual_qty=2.0,
	reorder_level=5.0,
	reorder_qty=20.0,
):
	return SimpleNamespace(
		item_code=item_code,
		item_name=item_name,
		warehouse=warehouse,
		actual_qty=actual_qty,
		reorder_level=reorder_level,
		reorder_qty=reorder_qty,
	)


# ── Mock factories ─────────────────────────────────────────────────────────────


class _PermError(Exception):
	pass


class _ValError(Exception):
	pass


def _base_frappe(*, is_manager: bool = True) -> MagicMock:
	m = MagicMock()
	m.db.exists.return_value = is_manager
	m.PermissionError = _PermError
	m.ValidationError = _ValError
	m.throw.side_effect = lambda msg, exc=Exception, **kw: (_ for _ in ()).throw(exc(msg))
	m.session = SimpleNamespace(user="mgr@test.surge")
	m.defaults.get_user_default.return_value = _COMPANY
	m.db.get_single_value.return_value = _COMPANY
	_cache = MagicMock()
	_cache.get_value.return_value = None
	m.cache.return_value = _cache
	return m


def _cust_frappe(*, is_manager: bool = True, rows=None) -> MagicMock:
	m = _base_frappe(is_manager=is_manager)
	m.db.sql.return_value = rows if rows is not None else []
	return m


def _widget_frappe(*, is_manager: bool = True, top=None, low=None, recent=None) -> MagicMock:
	"""For get_widgets_data — sql called 3 times: top_products, low_stock, recent_items."""
	m = _base_frappe(is_manager=is_manager)
	m.db.sql.side_effect = [
		top if top is not None else [],
		low if low is not None else [],
		recent if recent is not None else [],
	]
	return m


def _period_frappe(*, is_manager: bool = True, rows=None) -> MagicMock:
	"""For get_top_products / get_recent_items — single sql call."""
	m = _base_frappe(is_manager=is_manager)
	m.db.sql.return_value = rows if rows is not None else []
	return m


# ── Call helpers ───────────────────────────────────────────────────────────────


def _call_customer_overview(mock, period="today") -> dict:
	from surge.api.dashboard import get_customer_overview

	with patch("surge.api.dashboard.frappe", mock):
		resp = get_customer_overview(period=period)
	return orjson.loads(resp.get_data())


def _call_top_products(mock, period="today") -> list:
	from surge.api.dashboard import get_top_products

	with patch("surge.api.dashboard.frappe", mock):
		resp = get_top_products(period=period)
	return orjson.loads(resp.get_data())


def _call_recent_items(mock, period="today") -> list:
	from surge.api.dashboard import get_recent_items

	with patch("surge.api.dashboard.frappe", mock):
		resp = get_recent_items(period=period)
	return orjson.loads(resp.get_data())


def _call_widgets(mock) -> dict:
	from surge.api.dashboard import get_widgets_data

	with patch("surge.api.dashboard.frappe", mock):
		resp = get_widgets_data()
	return orjson.loads(resp.get_data())


def _sql_str(mock, call_index: int = 0) -> str:
	return str(mock.db.sql.call_args_list[call_index].args[0])


# ── H: get_customer_overview ──────────────────────────────────────────────────


class TestCustomerOverview(unittest.TestCase):
	def test_H01_all_five_periods_accepted(self):
		"""H01: All five calendar periods are valid — no exception raised."""
		for period in ("today", "this_week", "last_week", "this_month", "last_month"):
			m = _cust_frappe()
			try:
				_call_customer_overview(m, period=period)
			except Exception as exc:
				self.fail(f"Period '{period}' raised unexpectedly: {exc}")

	def test_H02_invalid_period_raises_validation_error(self):
		"""H02: An unknown period string raises ValidationError."""
		m = _cust_frappe()
		with self.assertRaises(_ValError):
			_call_customer_overview(m, period="yesterday")

	def test_H03_empty_rows_returns_all_zeros(self):
		"""H03: No invoices in period → zeros across the board."""
		data = _call_customer_overview(_cust_frappe(rows=[]))
		self.assertEqual(data["first_time"], 0)
		self.assertEqual(data["returning"], 0)
		self.assertEqual(data["total"], 0)
		self.assertEqual(data["first_time_pct"], 0)
		self.assertEqual(data["returning_pct"], 0)

	def test_H04_non_manager_blocked(self):
		"""H04: Non-manager user raises PermissionError before any DB query."""
		m = _cust_frappe(is_manager=False)
		with self.assertRaises(_PermError):
			_call_customer_overview(m)
		m.db.sql.assert_not_called()

	def test_H05_counts_first_time_and_returning_correctly(self):
		"""H05: 3 first_time + 2 returning rows → correct counts."""
		rows = [
			_cust_row("first_time", "C1"),
			_cust_row("first_time", "C2"),
			_cust_row("first_time", "C3"),
			_cust_row("returning", "C4"),
			_cust_row("returning", "C5"),
		]
		data = _call_customer_overview(_cust_frappe(rows=rows))
		self.assertEqual(data["first_time"], 3)
		self.assertEqual(data["returning"], 2)
		self.assertEqual(data["total"], 5)

	def test_H06_percentages_rounded_correctly(self):
		"""H06: 1 first_time / 3 total → 33%, 2 returning / 3 total → 67%."""
		rows = [
			_cust_row("first_time", "C1"),
			_cust_row("returning", "C2"),
			_cust_row("returning", "C3"),
		]
		data = _call_customer_overview(_cust_frappe(rows=rows))
		self.assertEqual(data["first_time_pct"], 33)
		self.assertEqual(data["returning_pct"], 67)

	def test_H07_all_first_time_gives_zero_returning_pct(self):
		"""H07: All customers are first-time → returning_pct = 0."""
		rows = [_cust_row("first_time", f"C{i}") for i in range(4)]
		data = _call_customer_overview(_cust_frappe(rows=rows))
		self.assertEqual(data["returning_pct"], 0)
		self.assertEqual(data["first_time_pct"], 100)


# ── P: get_top_products ───────────────────────────────────────────────────────


class TestTopProducts(unittest.TestCase):
	def test_P01_all_four_periods_accepted(self):
		"""P01: today / week / month / all are all valid."""
		for period in ("today", "week", "month", "all"):
			m = _period_frappe()
			try:
				_call_top_products(m, period=period)
			except Exception as exc:
				self.fail(f"Period '{period}' raised unexpectedly: {exc}")

	def test_P02_invalid_period_raises_validation_error(self):
		"""P02: Unknown period raises ValidationError."""
		m = _period_frappe()
		with self.assertRaises(_ValError):
			_call_top_products(m, period="quarterly")

	def test_P03_empty_result_returns_empty_list(self):
		"""P03: No data → [] response (not null, not error)."""
		data = _call_top_products(_period_frappe(rows=[]))
		self.assertEqual(data, [])

	def test_P04_non_manager_blocked(self):
		"""P04: Non-manager raises PermissionError; SQL never called."""
		m = _period_frappe(is_manager=False)
		with self.assertRaises(_PermError):
			_call_top_products(m)
		m.db.sql.assert_not_called()

	def test_P05_response_shape(self):
		"""P05: Each row has item_code, item_name, total_qty, total_amount."""
		rows = [_top_row("BEER-001", "Beer", 15.0, 1500.0)]
		data = _call_top_products(_period_frappe(rows=rows))
		self.assertEqual(len(data), 1)
		row = data[0]
		for field in ("item_code", "item_name", "total_qty", "total_amount"):
			self.assertIn(field, row, f"Missing field: {field}")
		self.assertEqual(row["item_code"], "BEER-001")
		self.assertAlmostEqual(row["total_qty"], 15.0)

	def test_P06_week_period_uses_six_day_interval(self):
		"""P06: 'week' period appends INTERVAL 6 DAY to SQL."""
		m = _period_frappe()
		_call_top_products(m, period="week")
		sql = _sql_str(m)
		self.assertIn("INTERVAL 6 DAY", sql)

	def test_P07_today_period_uses_curdate(self):
		"""P07: 'today' period uses CURDATE() equality filter."""
		m = _period_frappe()
		_call_top_products(m, period="today")
		sql = _sql_str(m)
		self.assertIn("CURDATE()", sql)

	def test_P08_all_period_adds_no_date_filter(self):
		"""P08: 'all' period has no date WHERE clause in the SQL."""
		m = _period_frappe()
		_call_top_products(m, period="all")
		sql = _sql_str(m)
		# The 'all' period_filter is "" so CURDATE and INTERVAL should be absent
		self.assertNotIn("CURDATE()", sql)
		self.assertNotIn("INTERVAL", sql)


# ── R: get_recent_items ───────────────────────────────────────────────────────


class TestRecentItems(unittest.TestCase):
	def test_R01_all_four_periods_accepted(self):
		"""R01: today / week / month / all are all valid."""
		for period in ("today", "week", "month", "all"):
			m = _period_frappe()
			try:
				_call_recent_items(m, period=period)
			except Exception as exc:
				self.fail(f"Period '{period}' raised unexpectedly: {exc}")

	def test_R02_invalid_period_raises_validation_error(self):
		"""R02: Unknown period raises ValidationError."""
		m = _period_frappe()
		with self.assertRaises(_ValError):
			_call_recent_items(m, period="last_year")

	def test_R03_empty_result_returns_empty_list(self):
		"""R03: No sale items in period → [] (not error)."""
		data = _call_recent_items(_period_frappe(rows=[]))
		self.assertEqual(data, [])

	def test_R04_non_manager_blocked(self):
		"""R04: Non-manager raises PermissionError; SQL never called."""
		m = _period_frappe(is_manager=False)
		with self.assertRaises(_PermError):
			_call_recent_items(m)
		m.db.sql.assert_not_called()

	def test_R05_response_shape(self):
		"""R05: Each row has all required fields."""
		rows = [_recent_row()]
		data = _call_recent_items(_period_frappe(rows=rows))
		self.assertEqual(len(data), 1)
		row = data[0]
		for field in (
			"item_code",
			"item_name",
			"item_group",
			"rate",
			"qty",
			"invoice",
			"posting_date",
			"status",
		):
			self.assertIn(field, row, f"Missing field: {field}")

	def test_R06_multi_invoice_five_items_returned(self):
		"""R06: 2 items from SINV-001 + 3 items from SINV-002 → all 5 returned."""
		rows = [
			_recent_row(item_code=f"ITEM-{i}", invoice="SINV-001" if i < 2 else "SINV-002") for i in range(5)
		]
		data = _call_recent_items(_period_frappe(rows=rows))
		self.assertEqual(len(data), 5)
		invoices = {r["invoice"] for r in data}
		self.assertIn("SINV-001", invoices)
		self.assertIn("SINV-002", invoices)

	def test_R07_single_invoice_five_items(self):
		"""R07: One invoice with 5 line items → all 5 items returned."""
		rows = [_recent_row(item_code=f"ITEM-{i}", invoice="SINV-100") for i in range(5)]
		data = _call_recent_items(_period_frappe(rows=rows))
		self.assertEqual(len(data), 5)
		self.assertTrue(all(r["invoice"] == "SINV-100" for r in data))

	def test_R08_status_empty_string_when_missing(self):
		"""R08: Rows with status=None are serialised as empty string, not null."""
		row = _recent_row(status="")
		# Simulate None coming from DB
		row.status = None
		data = _call_recent_items(_period_frappe(rows=[row]))
		self.assertEqual(data[0]["status"], "")


# ── W: get_widgets_data ───────────────────────────────────────────────────────


class TestWidgetsData(unittest.TestCase):
	def test_W01_low_stock_sql_does_not_reference_bin_reorder_level(self):
		"""W01: tabBin has no reorder_level column — SQL must not reference b.reorder_level."""
		m = _widget_frappe()
		_call_widgets(m)
		# Second sql call is the low_stock query
		sql = _sql_str(m, call_index=1)
		# Must NOT have b.reorder_level (b is the tabBin alias)
		self.assertNotRegex(sql, r"b\.reorder_level")
		# Must use ir.warehouse_reorder_level (from tabItem Reorder)
		self.assertIn("warehouse_reorder_level", sql)

	def test_W02_response_has_required_top_level_keys(self):
		"""W02: Response contains top_products, low_stock, and recent_items."""
		data = _call_widgets(_widget_frappe())
		for key in ("top_products", "low_stock", "recent_items"):
			self.assertIn(key, data, f"Missing key: {key}")

	def test_W03_low_stock_row_shape(self):
		"""W03: Each low_stock row has all required fields."""
		m = _widget_frappe(low=[_low_row()])
		data = _call_widgets(m)
		row = data["low_stock"][0]
		for field in ("item_code", "item_name", "warehouse", "actual_qty", "reorder_level", "reorder_qty"):
			self.assertIn(field, row, f"Missing low_stock field: {field}")

	def test_W04_non_manager_blocked(self):
		"""W04: Non-manager user raises PermissionError before any SQL."""
		m = _widget_frappe(is_manager=False)
		with self.assertRaises(_PermError):
			_call_widgets(m)
		m.db.sql.assert_not_called()

	def test_W05_cache_hit_skips_all_sql(self):
		"""W05: Cache hit returns cached payload without any DB query."""
		m = _widget_frappe()
		m.cache.return_value.get_value.return_value = {
			"top_products": [],
			"low_stock": [],
			"recent_items": [],
		}
		data = _call_widgets(m)
		m.db.sql.assert_not_called()
		self.assertEqual(data["top_products"], [])


if __name__ == "__main__":
	unittest.main()
